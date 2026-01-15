"""
Org-Skin Chatbot

Natural language interface for GitHub organization management.
Encodes GraphQL queries as AIML expressions and executes workflows.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Callable
import logging

from org_skin.graphql.client import GitHubGraphQLClient
from org_skin.aiml.encoder import AIMLEncoder, Intent, IntentType
from org_skin.aiml.parser import AIMLParser, ParsedTemplate
from org_skin.aiml.templates import AIMLTemplateEngine
from org_skin.mapper.scanner import OrganizationMapper
from org_skin.chatbot.nlp import NLPProcessor
from org_skin.chatbot.session import ChatSession, Message, MessageRole

logger = logging.getLogger(__name__)


@dataclass
class BotResponse:
    """Response from the chatbot."""
    text: str
    data: Optional[dict[str, Any]] = None
    graphql_executed: bool = False
    aiml_pattern: Optional[str] = None
    suggestions: list[str] = field(default_factory=list)
    error: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "data": self.data,
            "graphql_executed": self.graphql_executed,
            "aiml_pattern": self.aiml_pattern,
            "suggestions": self.suggestions,
            "error": self.error,
        }


class OrgSkinBot:
    """
    Intelligent chatbot for GitHub organization management.
    
    Features:
    - Natural language understanding
    - GraphQL query generation and execution
    - AIML pattern matching and learning
    - Multi-turn conversation support
    - Workflow automation
    """
    
    def __init__(
        self,
        organization: str = "skintwin-ai",
        github_token: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        """
        Initialize the chatbot.
        
        Args:
            organization: Default organization to operate on.
            github_token: GitHub Personal Access Token.
            openai_api_key: OpenAI API key for NLP (optional).
        """
        self.organization = organization
        self.github_token = github_token
        
        # Initialize components
        self.encoder = AIMLEncoder()
        self.parser = AIMLParser()
        self.template_engine = AIMLTemplateEngine()
        self.nlp = NLPProcessor(api_key=openai_api_key)
        
        # Session management
        self.sessions: dict[str, ChatSession] = {}
        self.default_session = ChatSession()
        
        # GraphQL client (initialized on demand)
        self._client: Optional[GitHubGraphQLClient] = None
        
        # Organization mapper (initialized on demand)
        self._mapper: Optional[OrganizationMapper] = None
        
        # Custom handlers
        self._handlers: dict[str, Callable] = {}
        self._setup_default_handlers()
    
    def _setup_default_handlers(self) -> None:
        """Set up default command handlers."""
        self._handlers["help"] = self._handle_help
        self._handlers["list_repos"] = self._handle_list_repos
        self._handlers["describe_repo"] = self._handle_describe_repo
        self._handlers["list_issues"] = self._handle_list_issues
        self._handlers["create_issue"] = self._handle_create_issue
        self._handlers["org_overview"] = self._handle_org_overview
        self._handlers["scan_org"] = self._handle_scan_org
        self._handlers["encode_pattern"] = self._handle_encode_pattern
    
    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
    ) -> BotResponse:
        """
        Process a chat message and return a response.
        
        Args:
            message: User message.
            session_id: Optional session ID for multi-turn conversations.
            
        Returns:
            BotResponse with text and optional data.
        """
        # Get or create session
        session = self.sessions.get(session_id, self.default_session) if session_id else self.default_session
        
        # Add user message to session
        session.add_message(Message(
            role=MessageRole.USER,
            content=message,
        ))
        
        try:
            # Parse intent
            intent = self.encoder.parse_intent(message)
            logger.info(f"Parsed intent: {intent.type.value} - {intent.action}")
            
            # Try AIML pattern matching first
            pattern_result = self.encoder.match_pattern(message)
            if pattern_result:
                category, wildcards = pattern_result
                response = await self._execute_pattern(category, wildcards, session)
                session.add_message(Message(
                    role=MessageRole.ASSISTANT,
                    content=response.text,
                    metadata={"aiml_pattern": category.pattern},
                ))
                return response
            
            # Try handler-based processing
            handler = self._find_handler(intent)
            if handler:
                response = await handler(intent, session)
                session.add_message(Message(
                    role=MessageRole.ASSISTANT,
                    content=response.text,
                ))
                return response
            
            # Fall back to NLP-based processing
            response = await self._process_with_nlp(message, intent, session)
            session.add_message(Message(
                role=MessageRole.ASSISTANT,
                content=response.text,
            ))
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_response = BotResponse(
                text=f"I encountered an error: {str(e)}. Please try rephrasing your request.",
                error=str(e),
                suggestions=[
                    "Try 'help' for available commands",
                    "Try 'list repos' to see repositories",
                ],
            )
            session.add_message(Message(
                role=MessageRole.ASSISTANT,
                content=error_response.text,
            ))
            return error_response
    
    async def _execute_pattern(
        self,
        category,
        wildcards: dict[str, str],
        session: ChatSession,
    ) -> BotResponse:
        """Execute an AIML pattern."""
        # Parse the template
        parsed = self.parser.parse_template(category.template, wildcards)
        
        # If there's a GraphQL query, execute it
        if parsed.graphql:
            result = await self._execute_graphql(parsed.graphql, parsed.variables)
            return BotResponse(
                text=self._format_graphql_result(result),
                data=result,
                graphql_executed=True,
                aiml_pattern=category.pattern,
            )
        
        # If there's a workflow, execute it
        if parsed.workflow:
            result = await self._execute_workflow(parsed.workflow)
            return BotResponse(
                text=f"Workflow '{parsed.workflow.name}' completed.",
                data=result,
                aiml_pattern=category.pattern,
            )
        
        # Return template text
        rendered = self.template_engine.render(category.template, wildcards)
        return BotResponse(
            text=rendered.output,
            aiml_pattern=category.pattern,
        )
    
    def _find_handler(self, intent: Intent) -> Optional[Callable]:
        """Find a handler for the given intent."""
        # Map actions to handlers
        action_mapping = {
            "list_repos": "list_repos",
            "list_repositories": "list_repos",
            "show_repos": "list_repos",
            "describe_repo": "describe_repo",
            "describe_repository": "describe_repo",
            "list_issues": "list_issues",
            "show_issues": "list_issues",
            "create_issue": "create_issue",
            "org_overview": "org_overview",
            "get_org": "org_overview",
            "scan_org": "scan_org",
            "map_org": "scan_org",
            "encode_pattern": "encode_pattern",
            "unknown": None,
        }
        
        handler_name = action_mapping.get(intent.action)
        if handler_name:
            return self._handlers.get(handler_name)
        
        # Check for help intent
        if intent.type == IntentType.HELP:
            return self._handlers.get("help")
        
        return None
    
    async def _process_with_nlp(
        self,
        message: str,
        intent: Intent,
        session: ChatSession,
    ) -> BotResponse:
        """Process message using NLP when pattern matching fails."""
        # Try to understand the query using NLP
        understanding = await self.nlp.understand(message, session.get_context())
        
        if understanding.get("action"):
            # NLP identified an action
            action = understanding["action"]
            entities = understanding.get("entities", {})
            
            # Create a synthetic intent
            synthetic_intent = Intent(
                type=IntentType.QUERY,
                action=action,
                entities=entities,
                raw_input=message,
            )
            
            handler = self._find_handler(synthetic_intent)
            if handler:
                return await handler(synthetic_intent, session)
        
        # Default response
        return BotResponse(
            text="I'm not sure how to help with that. Here are some things I can do:",
            suggestions=[
                "List repositories: 'list repos'",
                "Describe a repo: 'describe repo org-skin'",
                "Show issues: 'show issues in org-skin'",
                "Organization overview: 'org overview'",
                "Scan organization: 'scan org'",
            ],
        )
    
    async def _execute_graphql(
        self,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a GraphQL query."""
        if self._client is None:
            self._client = GitHubGraphQLClient(token=self.github_token)
        
        async with self._client:
            result = await self._client.execute(query, variables)
            if result.success:
                return result.data
            else:
                raise Exception(f"GraphQL error: {result.errors}")
    
    async def _execute_workflow(self, workflow) -> dict[str, Any]:
        """Execute a workflow."""
        results = {}
        
        for step in workflow.steps:
            if step.operation_type == "graphql":
                result = await self._execute_graphql(step.operation, step.variables)
                results[step.name] = result
                # Update parser context with results
                for key, value in self._flatten_dict(result).items():
                    self.parser.set_context(f"{step.name}.{key}", value)
            
            elif step.operation_type == "mutation":
                result = await self._execute_graphql(step.operation, step.variables)
                results[step.name] = result
        
        return results
    
    def _flatten_dict(self, d: dict, parent_key: str = '') -> dict:
        """Flatten a nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _format_graphql_result(self, data: dict[str, Any]) -> str:
        """Format GraphQL result for display."""
        # Simple formatting - can be enhanced
        return json.dumps(data, indent=2, default=str)
    
    # Handler implementations
    async def _handle_help(self, intent: Intent, session: ChatSession) -> BotResponse:
        """Handle help requests."""
        return BotResponse(
            text="""**Org-Skin Bot Help**

I can help you manage the SkinTwin-AI organization. Here are my capabilities:

**Repository Commands:**
- `list repos` - List all repositories
- `describe repo <name>` - Get detailed info about a repository
- `show issues in <repo>` - List open issues

**Organization Commands:**
- `org overview` - Get organization summary
- `scan org` - Full organization scan and mapping

**Issue Commands:**
- `create issue in <repo> titled <title>` - Create a new issue

**AIML Commands:**
- `encode pattern <pattern>` - Create an AIML pattern

**Tips:**
- I understand natural language, so feel free to ask questions naturally
- Use 'help' anytime to see this message
""",
            suggestions=[
                "list repos",
                "org overview",
                "describe repo org-skin",
            ],
        )
    
    async def _handle_list_repos(self, intent: Intent, session: ChatSession) -> BotResponse:
        """Handle list repositories request."""
        query = """
        query($org: String!) {
            organization(login: $org) {
                repositories(first: 20, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    nodes {
                        name
                        description
                        url
                        primaryLanguage { name }
                        stargazerCount
                        updatedAt
                    }
                }
            }
        }
        """
        
        org = intent.entities.get("organization", self.organization)
        result = await self._execute_graphql(query, {"org": org})
        
        repos = result.get("organization", {}).get("repositories", {}).get("nodes", [])
        
        if not repos:
            return BotResponse(
                text=f"No repositories found in {org}.",
                data=result,
                graphql_executed=True,
            )
        
        # Format output
        lines = [f"**Repositories in {org}:**\n"]
        for repo in repos:
            lang = repo.get("primaryLanguage", {})
            lang_name = lang.get("name", "Unknown") if lang else "Unknown"
            stars = repo.get("stargazerCount", 0)
            desc = repo.get("description", "No description")[:50]
            lines.append(f"- **{repo['name']}** ({lang_name}, ⭐{stars})")
            lines.append(f"  {desc}")
        
        return BotResponse(
            text="\n".join(lines),
            data=result,
            graphql_executed=True,
            suggestions=[f"describe repo {repos[0]['name']}" if repos else "org overview"],
        )
    
    async def _handle_describe_repo(self, intent: Intent, session: ChatSession) -> BotResponse:
        """Handle describe repository request."""
        repo_name = intent.entities.get("repository", "org-skin")
        org = intent.entities.get("organization", self.organization)
        
        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                name
                description
                url
                primaryLanguage { name }
                defaultBranchRef { name }
                stargazerCount
                forkCount
                diskUsage
                issues(states: OPEN) { totalCount }
                pullRequests(states: OPEN) { totalCount }
                languages(first: 10) {
                    nodes { name }
                }
                repositoryTopics(first: 10) {
                    nodes { topic { name } }
                }
            }
        }
        """
        
        result = await self._execute_graphql(query, {"owner": org, "name": repo_name})
        repo = result.get("repository", {})
        
        if not repo:
            return BotResponse(
                text=f"Repository '{repo_name}' not found in {org}.",
                error="Repository not found",
            )
        
        # Format output
        lang = repo.get("primaryLanguage", {})
        lang_name = lang.get("name", "Unknown") if lang else "Unknown"
        languages = [l.get("name", "") for l in repo.get("languages", {}).get("nodes", [])]
        topics = [t.get("topic", {}).get("name", "") for t in repo.get("repositoryTopics", {}).get("nodes", [])]
        
        text = f"""**{repo['name']}**

{repo.get('description', 'No description')}

**Details:**
- URL: {repo.get('url', 'N/A')}
- Primary Language: {lang_name}
- Default Branch: {repo.get('defaultBranchRef', {}).get('name', 'main') if repo.get('defaultBranchRef') else 'main'}
- Stars: {repo.get('stargazerCount', 0)} | Forks: {repo.get('forkCount', 0)}
- Open Issues: {repo.get('issues', {}).get('totalCount', 0)}
- Open PRs: {repo.get('pullRequests', {}).get('totalCount', 0)}
- Languages: {', '.join(languages) if languages else 'None'}
- Topics: {', '.join(topics) if topics else 'None'}
"""
        
        return BotResponse(
            text=text,
            data=result,
            graphql_executed=True,
            suggestions=[
                f"show issues in {repo_name}",
                "list repos",
            ],
        )
    
    async def _handle_list_issues(self, intent: Intent, session: ChatSession) -> BotResponse:
        """Handle list issues request."""
        repo_name = intent.entities.get("repository", "org-skin")
        org = intent.entities.get("organization", self.organization)
        
        query = """
        query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                issues(first: 20, states: OPEN, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    totalCount
                    nodes {
                        number
                        title
                        state
                        author { login }
                        createdAt
                        labels(first: 5) {
                            nodes { name }
                        }
                    }
                }
            }
        }
        """
        
        result = await self._execute_graphql(query, {"owner": org, "name": repo_name})
        issues_data = result.get("repository", {}).get("issues", {})
        issues = issues_data.get("nodes", [])
        total = issues_data.get("totalCount", 0)
        
        if not issues:
            return BotResponse(
                text=f"No open issues in {repo_name}.",
                data=result,
                graphql_executed=True,
            )
        
        lines = [f"**Open Issues in {repo_name}** ({total} total)\n"]
        for issue in issues:
            labels = [l.get("name", "") for l in issue.get("labels", {}).get("nodes", [])]
            labels_str = f" [{', '.join(labels)}]" if labels else ""
            author = issue.get("author", {})
            author_login = author.get("login", "unknown") if author else "unknown"
            lines.append(f"- #{issue['number']}: {issue['title']}{labels_str}")
            lines.append(f"  by @{author_login}")
        
        return BotResponse(
            text="\n".join(lines),
            data=result,
            graphql_executed=True,
        )
    
    async def _handle_create_issue(self, intent: Intent, session: ChatSession) -> BotResponse:
        """Handle create issue request."""
        # This would need more context from the user
        return BotResponse(
            text="To create an issue, I need more information. Please provide:\n- Repository name\n- Issue title\n- Issue body (optional)",
            suggestions=[
                "create issue in org-skin titled 'Bug Report'",
            ],
        )
    
    async def _handle_org_overview(self, intent: Intent, session: ChatSession) -> BotResponse:
        """Handle organization overview request."""
        org = intent.entities.get("organization", self.organization)
        
        query = """
        query($org: String!) {
            organization(login: $org) {
                name
                description
                url
                avatarUrl
                repositories { totalCount }
                teams { totalCount }
                membersWithRole { totalCount }
            }
        }
        """
        
        result = await self._execute_graphql(query, {"org": org})
        org_data = result.get("organization", {})
        
        if not org_data:
            return BotResponse(
                text=f"Organization '{org}' not found.",
                error="Organization not found",
            )
        
        text = f"""**{org_data.get('name', org)}**

{org_data.get('description', 'No description')}

**Statistics:**
- Repositories: {org_data.get('repositories', {}).get('totalCount', 0)}
- Teams: {org_data.get('teams', {}).get('totalCount', 0)}
- Members: {org_data.get('membersWithRole', {}).get('totalCount', 0)}

URL: {org_data.get('url', 'N/A')}
"""
        
        return BotResponse(
            text=text,
            data=result,
            graphql_executed=True,
            suggestions=["list repos", "scan org"],
        )
    
    async def _handle_scan_org(self, intent: Intent, session: ChatSession) -> BotResponse:
        """Handle organization scan request."""
        org = intent.entities.get("organization", self.organization)
        
        if self._mapper is None:
            self._mapper = OrganizationMapper(
                GitHubGraphQLClient(token=self.github_token)
            )
        
        result = await self._mapper.scan(org, include_issues=True, include_prs=True)
        
        text = f"""**Organization Scan Complete**

Scanned: {org}
Time: {result.scan_time:.2f} seconds

**Entities Found:**
- Repositories: {len(result.repositories)}
- Teams: {len(result.teams)}
- Members: {len(result.members)}
- Issues: {len(result.issues)}
- Pull Requests: {len(result.pull_requests)}
- Relationships: {len(result.relationships)}

Total Entities: {result.total_entities}
"""
        
        return BotResponse(
            text=text,
            data={
                "scan_time": result.scan_time,
                "total_entities": result.total_entities,
                "repos": len(result.repositories),
                "teams": len(result.teams),
                "members": len(result.members),
            },
        )
    
    async def _handle_encode_pattern(self, intent: Intent, session: ChatSession) -> BotResponse:
        """Handle AIML pattern encoding request."""
        return BotResponse(
            text="""**AIML Pattern Encoding**

To encode a new pattern, provide:
1. Pattern (e.g., "LIST * REPOS")
2. Template (GraphQL query or response)

Example:
```
Pattern: GET INFO FOR * REPO
Template: <graphql>query { repository(name: "<star/>") { ... } }</graphql>
```

Current patterns: """ + str(len(self.encoder.patterns)),
            suggestions=["help", "list repos"],
        )
    
    def get_session(self, session_id: str) -> ChatSession:
        """Get or create a chat session."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(session_id=session_id)
        return self.sessions[session_id]
    
    def clear_session(self, session_id: str) -> None:
        """Clear a chat session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
