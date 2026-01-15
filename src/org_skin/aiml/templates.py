"""
AIML Template Engine

Renders AIML templates with variable substitution and GraphQL integration.
"""

import re
import json
from dataclasses import dataclass
from typing import Any, Callable, Optional
from jinja2 import Environment, BaseLoader
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemplateResult:
    """Result of template rendering."""
    output: str
    graphql_queries: list[str]
    mutations: list[str]
    variables: dict[str, Any]
    metadata: dict[str, Any]


class AIMLTemplateEngine:
    """
    Template engine for AIML with GraphQL extensions.
    
    Features:
    - Variable substitution
    - GraphQL query embedding
    - Conditional rendering
    - Loop support
    - Custom functions
    """
    
    def __init__(self):
        """Initialize the template engine."""
        self.jinja_env = Environment(loader=BaseLoader())
        self.context: dict[str, Any] = {}
        self.functions: dict[str, Callable] = {}
        self._setup_default_functions()
    
    def _setup_default_functions(self) -> None:
        """Set up default template functions."""
        self.functions['upper'] = str.upper
        self.functions['lower'] = str.lower
        self.functions['title'] = str.title
        self.functions['strip'] = str.strip
        self.functions['json'] = json.dumps
        self.functions['len'] = len
        self.functions['first'] = lambda x: x[0] if x else None
        self.functions['last'] = lambda x: x[-1] if x else None
        self.functions['join'] = lambda x, sep=', ': sep.join(str(i) for i in x)
    
    def register_function(self, name: str, func: Callable) -> None:
        """Register a custom template function."""
        self.functions[name] = func
    
    def set_context(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self.context[key] = value
    
    def get_context(self, key: str) -> Any:
        """Get a context variable."""
        return self.context.get(key)
    
    def clear_context(self) -> None:
        """Clear all context variables."""
        self.context.clear()
    
    def render(
        self,
        template: str,
        variables: dict[str, Any] = None,
    ) -> TemplateResult:
        """
        Render an AIML template.
        
        Args:
            template: Template string.
            variables: Template variables.
            
        Returns:
            TemplateResult with rendered output and metadata.
        """
        variables = variables or {}
        all_vars = {**self.context, **variables, **self.functions}
        
        graphql_queries = []
        mutations = []
        extracted_vars = {}
        
        # Extract and process GraphQL blocks
        def process_graphql(match):
            query = match.group(1).strip()
            graphql_queries.append(query)
            return f"[GraphQL Query #{len(graphql_queries)}]"
        
        template = re.sub(
            r'<graphql>(.*?)</graphql>',
            process_graphql,
            template,
            flags=re.DOTALL
        )
        
        # Extract and process mutation blocks
        def process_mutation(match):
            mutation = match.group(1).strip()
            mutations.append(mutation)
            return f"[Mutation #{len(mutations)}]"
        
        template = re.sub(
            r'<mutation>(.*?)</mutation>',
            process_mutation,
            template,
            flags=re.DOTALL
        )
        
        # Extract variables blocks
        def process_vars(match):
            try:
                vars_data = json.loads(match.group(1).strip())
                extracted_vars.update(vars_data)
            except json.JSONDecodeError:
                pass
            return ""
        
        template = re.sub(
            r'<vars>(.*?)</vars>',
            process_vars,
            template,
            flags=re.DOTALL
        )
        
        # Process think blocks (remove from output)
        template = re.sub(r'<think>.*?</think>', '', template, flags=re.DOTALL)
        
        # Process AIML tags
        template = self._process_aiml_tags(template, all_vars)
        
        # Process Jinja2 syntax
        try:
            jinja_template = self.jinja_env.from_string(template)
            output = jinja_template.render(**all_vars)
        except Exception as e:
            logger.warning(f"Jinja2 rendering failed: {e}")
            output = template
        
        # Clean up output
        output = re.sub(r'\n{3,}', '\n\n', output)
        output = output.strip()
        
        return TemplateResult(
            output=output,
            graphql_queries=graphql_queries,
            mutations=mutations,
            variables=extracted_vars,
            metadata={
                'query_count': len(graphql_queries),
                'mutation_count': len(mutations),
            }
        )
    
    def _process_aiml_tags(self, template: str, variables: dict[str, Any]) -> str:
        """Process AIML-specific tags."""
        # Process <star/> and <star index="N"/>
        def replace_star(match):
            index = match.group(1) or "1"
            key = f"star{index}"
            return str(variables.get(key, f"<star{index}>"))
        
        template = re.sub(r'<star(?:\s+index="(\d+)")?/>', replace_star, template)
        
        # Process <get name="..."/>
        def replace_get(match):
            name = match.group(1)
            return str(variables.get(name, self.context.get(name, f"<{name}>")))
        
        template = re.sub(r'<get\s+name="([^"]+)"/>', replace_get, template)
        
        # Process <set name="...">...</set>
        def replace_set(match):
            name = match.group(1)
            value = match.group(2)
            self.context[name] = value
            return value
        
        template = re.sub(r'<set\s+name="([^"]+)">(.*?)</set>', replace_set, template, flags=re.DOTALL)
        
        # Process <condition>
        template = self._process_conditions(template, variables)
        
        # Process <random>
        template = self._process_random(template)
        
        # Process <srai>
        template = self._process_srai(template, variables)
        
        return template
    
    def _process_conditions(self, template: str, variables: dict[str, Any]) -> str:
        """Process conditional blocks."""
        # Simple condition: <condition name="var" value="val">content</condition>
        def replace_condition(match):
            name = match.group(1)
            value = match.group(2)
            content = match.group(3)
            
            actual_value = str(variables.get(name, self.context.get(name, "")))
            if actual_value == value:
                return content
            return ""
        
        template = re.sub(
            r'<condition\s+name="([^"]+)"\s+value="([^"]+)">(.*?)</condition>',
            replace_condition,
            template,
            flags=re.DOTALL
        )
        
        return template
    
    def _process_random(self, template: str) -> str:
        """Process random selection blocks."""
        import random
        
        def replace_random(match):
            content = match.group(1)
            items = re.findall(r'<li>(.*?)</li>', content, re.DOTALL)
            if items:
                return random.choice(items).strip()
            return ""
        
        template = re.sub(
            r'<random>(.*?)</random>',
            replace_random,
            template,
            flags=re.DOTALL
        )
        
        return template
    
    def _process_srai(self, template: str, variables: dict[str, Any]) -> str:
        """Process symbolic reduction (SRAI) blocks."""
        # SRAI would normally trigger another pattern match
        # For now, we just return the content
        def replace_srai(match):
            return f"[SRAI: {match.group(1).strip()}]"
        
        template = re.sub(
            r'<srai>(.*?)</srai>',
            replace_srai,
            template,
            flags=re.DOTALL
        )
        
        return template


class GraphQLTemplateBuilder:
    """Builder for GraphQL query templates."""
    
    def __init__(self):
        """Initialize the builder."""
        self.templates: dict[str, str] = {}
        self._load_default_templates()
    
    def _load_default_templates(self) -> None:
        """Load default GraphQL templates."""
        self.templates = {
            'list_repos': '''
query ListRepos($org: String!, $first: Int = 100) {
  organization(login: $org) {
    repositories(first: $first, orderBy: {field: UPDATED_AT, direction: DESC}) {
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
''',
            'repo_details': '''
query RepoDetails($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    name
    description
    url
    primaryLanguage { name }
    defaultBranchRef { name }
    stargazerCount
    forkCount
    issues(states: OPEN) { totalCount }
    pullRequests(states: OPEN) { totalCount }
    languages(first: 10) {
      nodes { name }
    }
  }
}
''',
            'org_overview': '''
query OrgOverview($org: String!) {
  organization(login: $org) {
    name
    description
    url
    repositories { totalCount }
    teams { totalCount }
    membersWithRole { totalCount }
  }
}
''',
            'create_issue': '''
mutation CreateIssue($input: CreateIssueInput!) {
  createIssue(input: $input) {
    issue {
      number
      title
      url
    }
  }
}
''',
            'add_comment': '''
mutation AddComment($input: AddCommentInput!) {
  addComment(input: $input) {
    commentEdge {
      node {
        id
        body
        createdAt
      }
    }
  }
}
''',
        }
    
    def get_template(self, name: str) -> Optional[str]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def add_template(self, name: str, template: str) -> None:
        """Add a new template."""
        self.templates[name] = template
    
    def list_templates(self) -> list[str]:
        """List all template names."""
        return list(self.templates.keys())
    
    def render_template(
        self,
        name: str,
        variables: dict[str, Any] = None,
    ) -> Optional[tuple[str, dict[str, Any]]]:
        """
        Render a template with variables.
        
        Returns:
            Tuple of (query_string, variables_dict) or None.
        """
        template = self.get_template(name)
        if not template:
            return None
        
        return template.strip(), variables or {}
