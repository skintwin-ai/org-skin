"""
AIML Expression Encoder

Transforms natural language queries and GraphQL operations into AIML-compatible expressions.
Provides bidirectional mapping between GraphQL and AIML patterns.
"""

import re
import json
import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Types of user intents."""
    QUERY = "query"
    MUTATION = "mutation"
    WORKFLOW = "workflow"
    ANALYSIS = "analysis"
    HELP = "help"


@dataclass
class Intent:
    """Represents a parsed user intent."""
    type: IntentType
    action: str
    entities: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    raw_input: str = ""


@dataclass
class AIMLCategory:
    """Represents an AIML category (pattern-template pair)."""
    pattern: str
    template: str
    topic: str = "*"
    that: str = "*"
    
    def to_xml(self) -> str:
        """Convert category to AIML XML format."""
        xml = f'<category>\n  <pattern>{self.pattern}</pattern>\n'
        if self.that != "*":
            xml += f'  <that>{self.that}</that>\n'
        xml += f'  <template>{self.template}</template>\n</category>'
        return xml


@dataclass
class GraphQLMapping:
    """Maps an AIML pattern to a GraphQL operation."""
    pattern: str
    query_template: str
    variables_extractor: Callable[[dict[str, str]], dict[str, Any]]
    response_formatter: Callable[[dict[str, Any]], str]


class AIMLEncoder:
    """
    Encodes GraphQL operations as AIML expressions.
    
    Features:
    - Pattern recognition for natural language queries
    - GraphQL query generation from patterns
    - Response formatting for conversational output
    - Knowledge base management
    """
    
    def __init__(self):
        """Initialize the AIML encoder."""
        self.patterns: dict[str, AIMLCategory] = {}
        self.mappings: dict[str, GraphQLMapping] = {}
        self.knowledge_base: dict[str, Any] = {}
        self._setup_default_patterns()
    
    def _setup_default_patterns(self) -> None:
        """Set up default AIML patterns for GitHub operations."""
        # Organization patterns
        self.add_pattern(
            "LIST * REPOS",
            self._create_list_repos_template(),
            topic="organization"
        )
        self.add_pattern(
            "SHOW * REPOSITORIES",
            self._create_list_repos_template(),
            topic="organization"
        )
        self.add_pattern(
            "GET ORG * INFO",
            self._create_org_info_template(),
            topic="organization"
        )
        
        # Repository patterns
        self.add_pattern(
            "DESCRIBE REPO *",
            self._create_repo_details_template(),
            topic="repository"
        )
        self.add_pattern(
            "LIST FILES IN *",
            self._create_list_files_template(),
            topic="repository"
        )
        self.add_pattern(
            "SHOW ISSUES IN *",
            self._create_list_issues_template(),
            topic="repository"
        )
        
        # Action patterns
        self.add_pattern(
            "CREATE ISSUE IN * TITLED *",
            self._create_issue_template(),
            topic="actions"
        )
        self.add_pattern(
            "ADD COMMENT TO ISSUE * IN * SAYING *",
            self._create_comment_template(),
            topic="actions"
        )
        
        # Analysis patterns
        self.add_pattern(
            "ANALYZE * CODEBASE",
            self._create_analysis_template(),
            topic="analysis"
        )
        self.add_pattern(
            "COMPARE * AND *",
            self._create_compare_template(),
            topic="analysis"
        )
        
        # Help patterns
        self.add_pattern(
            "HELP",
            self._create_help_template(),
            topic="help"
        )
        self.add_pattern(
            "WHAT CAN YOU DO",
            self._create_capabilities_template(),
            topic="help"
        )
    
    def add_pattern(
        self,
        pattern: str,
        template: str,
        topic: str = "*",
        that: str = "*",
    ) -> None:
        """Add an AIML pattern to the encoder."""
        category = AIMLCategory(
            pattern=pattern.upper(),
            template=template,
            topic=topic,
            that=that,
        )
        pattern_key = self._pattern_key(pattern)
        self.patterns[pattern_key] = category
        logger.debug(f"Added pattern: {pattern}")
    
    def add_graphql_mapping(
        self,
        pattern: str,
        query_template: str,
        variables_extractor: Callable[[dict[str, str]], dict[str, Any]],
        response_formatter: Callable[[dict[str, Any]], str],
    ) -> None:
        """Add a GraphQL mapping for a pattern."""
        mapping = GraphQLMapping(
            pattern=pattern.upper(),
            query_template=query_template,
            variables_extractor=variables_extractor,
            response_formatter=response_formatter,
        )
        pattern_key = self._pattern_key(pattern)
        self.mappings[pattern_key] = mapping
    
    def _pattern_key(self, pattern: str) -> str:
        """Generate a unique key for a pattern."""
        normalized = pattern.upper().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def match_pattern(self, input_text: str) -> Optional[tuple[AIMLCategory, dict[str, str]]]:
        """
        Match input text against registered patterns.
        
        Returns:
            Tuple of (matched category, extracted wildcards) or None.
        """
        normalized_input = input_text.upper().strip()
        
        for key, category in self.patterns.items():
            wildcards = self._extract_wildcards(category.pattern, normalized_input)
            if wildcards is not None:
                return category, wildcards
        
        return None
    
    def _extract_wildcards(
        self,
        pattern: str,
        input_text: str,
    ) -> Optional[dict[str, str]]:
        """Extract wildcard values from input based on pattern."""
        # Convert AIML pattern to regex
        regex_pattern = pattern
        regex_pattern = regex_pattern.replace("*", "(.+)")
        regex_pattern = regex_pattern.replace("_", "(\\S+)")
        regex_pattern = f"^{regex_pattern}$"
        
        match = re.match(regex_pattern, input_text, re.IGNORECASE)
        if match:
            wildcards = {}
            for i, group in enumerate(match.groups(), 1):
                wildcards[f"star{i}"] = group.strip()
            return wildcards
        
        return None
    
    def encode_query(self, natural_language: str) -> Optional[dict[str, Any]]:
        """
        Encode a natural language query into GraphQL.
        
        Args:
            natural_language: Natural language query string.
            
        Returns:
            Dict with 'query', 'variables', and 'formatter' keys, or None.
        """
        result = self.match_pattern(natural_language)
        if not result:
            return None
        
        category, wildcards = result
        pattern_key = self._pattern_key(category.pattern)
        
        if pattern_key in self.mappings:
            mapping = self.mappings[pattern_key]
            variables = mapping.variables_extractor(wildcards)
            return {
                "query": mapping.query_template,
                "variables": variables,
                "formatter": mapping.response_formatter,
            }
        
        return {
            "pattern": category.pattern,
            "template": category.template,
            "wildcards": wildcards,
        }
    
    def parse_intent(self, input_text: str) -> Intent:
        """
        Parse user input to determine intent.
        
        Args:
            input_text: User input string.
            
        Returns:
            Intent object with type, action, and entities.
        """
        normalized = input_text.upper().strip()
        
        # Detect intent type
        if any(kw in normalized for kw in ["CREATE", "ADD", "UPDATE", "DELETE", "CLOSE", "MERGE"]):
            intent_type = IntentType.MUTATION
        elif any(kw in normalized for kw in ["ANALYZE", "COMPARE", "EVALUATE", "ASSESS"]):
            intent_type = IntentType.ANALYSIS
        elif any(kw in normalized for kw in ["HELP", "WHAT CAN", "HOW DO"]):
            intent_type = IntentType.HELP
        elif any(kw in normalized for kw in ["WORKFLOW", "AUTOMATE", "SCHEDULE"]):
            intent_type = IntentType.WORKFLOW
        else:
            intent_type = IntentType.QUERY
        
        # Extract action
        action_patterns = {
            "LIST": r"LIST\s+(\w+)",
            "SHOW": r"SHOW\s+(\w+)",
            "GET": r"GET\s+(\w+)",
            "CREATE": r"CREATE\s+(\w+)",
            "UPDATE": r"UPDATE\s+(\w+)",
            "DELETE": r"DELETE\s+(\w+)",
            "ANALYZE": r"ANALYZE\s+(\w+)",
        }
        
        action = "unknown"
        for action_name, pattern in action_patterns.items():
            if match := re.search(pattern, normalized):
                action = f"{action_name.lower()}_{match.group(1).lower()}"
                break
        
        # Extract entities
        entities = {}
        
        # Extract organization names
        if org_match := re.search(r"(?:IN|FOR|OF)\s+(\w+[-\w]*)\s+(?:ORG|ORGANIZATION)", normalized):
            entities["organization"] = org_match.group(1).lower()
        
        # Extract repository names
        if repo_match := re.search(r"(?:REPO|REPOSITORY)\s+(\w+[-\w]*)", normalized):
            entities["repository"] = repo_match.group(1).lower()
        
        # Extract issue/PR numbers
        if num_match := re.search(r"(?:ISSUE|PR|PULL REQUEST)\s+#?(\d+)", normalized):
            entities["number"] = int(num_match.group(1))
        
        return Intent(
            type=intent_type,
            action=action,
            entities=entities,
            raw_input=input_text,
        )
    
    def generate_aiml_file(self, topic: str = None) -> str:
        """
        Generate an AIML file from registered patterns.
        
        Args:
            topic: Optional topic filter.
            
        Returns:
            AIML XML string.
        """
        xml_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<aiml version="2.0">',
        ]
        
        for category in self.patterns.values():
            if topic is None or category.topic == topic:
                xml_parts.append(category.to_xml())
        
        xml_parts.append('</aiml>')
        return '\n'.join(xml_parts)
    
    def save_knowledge(self, filepath: str) -> None:
        """Save knowledge base to file."""
        data = {
            "patterns": {
                key: {
                    "pattern": cat.pattern,
                    "template": cat.template,
                    "topic": cat.topic,
                    "that": cat.that,
                }
                for key, cat in self.patterns.items()
            },
            "knowledge": self.knowledge_base,
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_knowledge(self, filepath: str) -> None:
        """Load knowledge base from file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for key, cat_data in data.get("patterns", {}).items():
            self.patterns[key] = AIMLCategory(**cat_data)
        
        self.knowledge_base = data.get("knowledge", {})
    
    # Template generators
    def _create_list_repos_template(self) -> str:
        return """<think>Listing repositories for organization <star/></think>
<graphql>
query($org: String!) {
  organization(login: $org) {
    repositories(first: 100) {
      nodes { name description url }
    }
  }
}
</graphql>
<vars>{"org": "<star/>"}</vars>"""
    
    def _create_org_info_template(self) -> str:
        return """<think>Getting organization info for <star/></think>
<graphql>
query($org: String!) {
  organization(login: $org) {
    name description url
    repositories { totalCount }
    teams { totalCount }
    membersWithRole { totalCount }
  }
}
</graphql>
<vars>{"org": "<star/>"}</vars>"""
    
    def _create_repo_details_template(self) -> str:
        return """<think>Getting details for repository <star/></think>
<graphql>
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name description url
    primaryLanguage { name }
    stargazerCount forkCount
    issues(states: OPEN) { totalCount }
    pullRequests(states: OPEN) { totalCount }
  }
}
</graphql>"""
    
    def _create_list_files_template(self) -> str:
        return """<think>Listing files in repository <star/></think>
<graphql>
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    object(expression: "HEAD:") {
      ... on Tree {
        entries { name type path }
      }
    }
  }
}
</graphql>"""
    
    def _create_list_issues_template(self) -> str:
        return """<think>Listing issues in repository <star/></think>
<graphql>
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    issues(first: 20, states: OPEN) {
      nodes { number title state author { login } }
    }
  }
}
</graphql>"""
    
    def _create_issue_template(self) -> str:
        return """<think>Creating issue in <star index="1"/> titled <star index="2"/></think>
<workflow name="create-issue">
  <step name="get-repo-id">
    <graphql>query { repository(owner: "skintwin-ai", name: "<star index="1"/>") { id } }</graphql>
  </step>
  <step name="create">
    <mutation>
      mutation($input: CreateIssueInput!) {
        createIssue(input: $input) {
          issue { number url }
        }
      }
    </mutation>
    <vars>{"input": {"repositoryId": "<get name='repo.id'/>", "title": "<star index='2'/>"}}</vars>
  </step>
</workflow>"""
    
    def _create_comment_template(self) -> str:
        return """<think>Adding comment to issue <star index="1"/> in <star index="2"/></think>
<workflow name="add-comment">
  <step name="get-issue">
    <graphql>
      query { repository(owner: "skintwin-ai", name: "<star index="2"/>") {
        issue(number: <star index="1"/>) { id }
      }}
    </graphql>
  </step>
  <step name="comment">
    <mutation>
      mutation($input: AddCommentInput!) {
        addComment(input: $input) { commentEdge { node { id } } }
      }
    </mutation>
    <vars>{"input": {"subjectId": "<get name='issue.id'/>", "body": "<star index='3'/>"}}</vars>
  </step>
</workflow>"""
    
    def _create_analysis_template(self) -> str:
        return """<think>Analyzing codebase of <star/></think>
<analysis type="codebase">
  <target><star/></target>
  <metrics>
    <metric name="languages"/>
    <metric name="complexity"/>
    <metric name="dependencies"/>
    <metric name="test_coverage"/>
  </metrics>
</analysis>"""
    
    def _create_compare_template(self) -> str:
        return """<think>Comparing <star index="1"/> and <star index="2"/></think>
<analysis type="comparison">
  <targets>
    <target><star index="1"/></target>
    <target><star index="2"/></target>
  </targets>
  <dimensions>
    <dimension name="structure"/>
    <dimension name="features"/>
    <dimension name="activity"/>
  </dimensions>
</analysis>"""
    
    def _create_help_template(self) -> str:
        return """I can help you with GitHub organization management. Here are some things I can do:

**Queries:**
- List repositories: "list skintwin-ai repos"
- Show repo details: "describe repo org-skin"
- List issues: "show issues in org-skin"

**Actions:**
- Create issue: "create issue in org-skin titled Bug Report"
- Add comment: "add comment to issue 1 in org-skin saying Fixed!"

**Analysis:**
- Analyze codebase: "analyze org-skin codebase"
- Compare repos: "compare skintwin and multiskin"

What would you like to do?"""
    
    def _create_capabilities_template(self) -> str:
        return """I am the Org-Skin chatbot, designed to help manage the SkinTwin-AI organization.

**My Capabilities:**

1. **Organization Mapping** - I can map all repositories, teams, and members
2. **GraphQL Queries** - I translate natural language to GitHub GraphQL API calls
3. **AIML Encoding** - I encode workflows as AIML patterns for reuse
4. **Feature Aggregation** - I analyze and combine features from all repos
5. **Workflow Automation** - I can execute multi-step workflows

**Supported Operations:**
- Repository management (list, describe, analyze)
- Issue tracking (create, update, close, comment)
- Pull request management (create, review, merge)
- Team and member management
- Cross-repo analysis and comparison

Ask me anything about the organization!"""
