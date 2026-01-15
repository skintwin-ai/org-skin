"""
GraphQL Query Builder

Dynamic query construction for GitHub GraphQL API.
Supports building complex queries with validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class FieldType(Enum):
    """GraphQL field types."""
    SCALAR = "scalar"
    OBJECT = "object"
    LIST = "list"
    CONNECTION = "connection"


@dataclass
class QueryField:
    """Represents a field in a GraphQL query."""
    name: str
    alias: Optional[str] = None
    arguments: dict[str, Any] = field(default_factory=dict)
    fields: list["QueryField"] = field(default_factory=list)
    
    def to_graphql(self, indent: int = 0) -> str:
        """Convert field to GraphQL string."""
        spaces = "  " * indent
        
        # Build field name with alias
        field_str = f"{self.alias}: {self.name}" if self.alias else self.name
        
        # Add arguments
        if self.arguments:
            args = ", ".join(
                f"{k}: {self._format_value(v)}" 
                for k, v in self.arguments.items()
            )
            field_str += f"({args})"
        
        # Add nested fields
        if self.fields:
            nested = "\n".join(f.to_graphql(indent + 1) for f in self.fields)
            field_str += f" {{\n{nested}\n{spaces}}}"
        
        return f"{spaces}{field_str}"
    
    def _format_value(self, value: Any) -> str:
        """Format a value for GraphQL."""
        if isinstance(value, str):
            if value.startswith("$"):
                return value  # Variable reference
            return f'"{value}"'
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            items = ", ".join(self._format_value(v) for v in value)
            return f"[{items}]"
        elif isinstance(value, dict):
            items = ", ".join(
                f"{k}: {self._format_value(v)}" 
                for k, v in value.items()
            )
            return f"{{{items}}}"
        elif value is None:
            return "null"
        return str(value)


@dataclass
class QueryVariable:
    """Represents a variable in a GraphQL query."""
    name: str
    type: str
    default: Optional[Any] = None
    required: bool = True
    
    def to_graphql(self) -> str:
        """Convert variable to GraphQL string."""
        type_str = self.type
        if self.required and not type_str.endswith("!"):
            type_str += "!"
        
        var_str = f"${self.name}: {type_str}"
        if self.default is not None:
            var_str += f" = {self._format_default()}"
        
        return var_str
    
    def _format_default(self) -> str:
        """Format default value."""
        if isinstance(self.default, str):
            return f'"{self.default}"'
        elif isinstance(self.default, bool):
            return str(self.default).lower()
        return str(self.default)


class QueryBuilder:
    """
    Dynamic GraphQL query builder.
    
    Example:
        builder = QueryBuilder("GetOrg")
        builder.add_variable("login", "String")
        builder.add_field("organization", {"login": "$login"}, [
            QueryField("name"),
            QueryField("repositories", {"first": 10}, [
                QueryField("nodes", fields=[
                    QueryField("name"),
                    QueryField("url"),
                ])
            ])
        ])
        query = builder.build()
    """
    
    def __init__(self, name: str = "Query"):
        """Initialize query builder."""
        self.name = name
        self.variables: list[QueryVariable] = []
        self.fields: list[QueryField] = []
    
    def add_variable(
        self,
        name: str,
        type: str,
        default: Optional[Any] = None,
        required: bool = True,
    ) -> "QueryBuilder":
        """Add a variable to the query."""
        self.variables.append(QueryVariable(name, type, default, required))
        return self
    
    def add_field(
        self,
        name: str,
        arguments: Optional[dict[str, Any]] = None,
        fields: Optional[list[QueryField]] = None,
        alias: Optional[str] = None,
    ) -> "QueryBuilder":
        """Add a field to the query."""
        self.fields.append(QueryField(
            name=name,
            alias=alias,
            arguments=arguments or {},
            fields=fields or [],
        ))
        return self
    
    def build(self) -> str:
        """Build the GraphQL query string."""
        # Build variable declarations
        var_str = ""
        if self.variables:
            vars_list = ", ".join(v.to_graphql() for v in self.variables)
            var_str = f"({vars_list})"
        
        # Build fields
        fields_str = "\n".join(f.to_graphql(1) for f in self.fields)
        
        return f"query {self.name}{var_str} {{\n{fields_str}\n}}"
    
    def __str__(self) -> str:
        return self.build()


# Pre-built query templates
class OrgQueries:
    """Organization-related query templates."""
    
    @staticmethod
    def list_repos(org: str, first: int = 100) -> tuple[str, dict[str, Any]]:
        """Query to list organization repositories."""
        query = """
        query ListOrgRepos($org: String!, $first: Int!, $after: String) {
            organization(login: $org) {
                repositories(first: $first, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        name
                        nameWithOwner
                        description
                        url
                        isPrivate
                        isArchived
                        primaryLanguage { name }
                        defaultBranchRef { name }
                        createdAt
                        updatedAt
                        pushedAt
                        stargazerCount
                        forkCount
                        diskUsage
                        languages(first: 10) {
                            nodes { name }
                        }
                        repositoryTopics(first: 10) {
                            nodes {
                                topic { name }
                            }
                        }
                    }
                }
            }
        }
        """
        return query, {"org": org, "first": first}
    
    @staticmethod
    def list_teams(org: str) -> tuple[str, dict[str, Any]]:
        """Query to list organization teams."""
        query = """
        query ListOrgTeams($org: String!, $first: Int!, $after: String) {
            organization(login: $org) {
                teams(first: $first, after: $after) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        name
                        slug
                        description
                        privacy
                        membersCount: members { totalCount }
                        reposCount: repositories { totalCount }
                    }
                }
            }
        }
        """
        return query, {"org": org, "first": 100}
    
    @staticmethod
    def list_members(org: str) -> tuple[str, dict[str, Any]]:
        """Query to list organization members."""
        query = """
        query ListOrgMembers($org: String!, $first: Int!, $after: String) {
            organization(login: $org) {
                membersWithRole(first: $first, after: $after) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        login
                        name
                        email
                        avatarUrl
                        bio
                        company
                        location
                    }
                }
            }
        }
        """
        return query, {"org": org, "first": 100}
    
    @staticmethod
    def org_overview(org: str) -> tuple[str, dict[str, Any]]:
        """Query for organization overview."""
        query = """
        query OrgOverview($org: String!) {
            organization(login: $org) {
                id
                name
                login
                description
                url
                avatarUrl
                websiteUrl
                email
                isVerified
                createdAt
                repositories { totalCount }
                teams { totalCount }
                membersWithRole { totalCount }
                projects(first: 10) {
                    totalCount
                    nodes {
                        name
                        state
                    }
                }
            }
        }
        """
        return query, {"org": org}


class RepoQueries:
    """Repository-related query templates."""
    
    @staticmethod
    def repo_details(owner: str, name: str) -> tuple[str, dict[str, Any]]:
        """Query for detailed repository information."""
        query = """
        query RepoDetails($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
                id
                name
                nameWithOwner
                description
                url
                homepageUrl
                isPrivate
                isArchived
                isFork
                primaryLanguage { name }
                defaultBranchRef { name }
                createdAt
                updatedAt
                pushedAt
                stargazerCount
                forkCount
                diskUsage
                licenseInfo { name spdxId }
                languages(first: 20) {
                    totalSize
                    edges {
                        size
                        node { name color }
                    }
                }
                repositoryTopics(first: 20) {
                    nodes {
                        topic { name }
                    }
                }
                issues(states: OPEN) { totalCount }
                pullRequests(states: OPEN) { totalCount }
                releases(first: 5) {
                    nodes {
                        name
                        tagName
                        publishedAt
                    }
                }
            }
        }
        """
        return query, {"owner": owner, "name": name}
    
    @staticmethod
    def repo_tree(owner: str, name: str, path: str = "HEAD:") -> tuple[str, dict[str, Any]]:
        """Query for repository file tree."""
        query = """
        query RepoTree($owner: String!, $name: String!, $expression: String!) {
            repository(owner: $owner, name: $name) {
                object(expression: $expression) {
                    ... on Tree {
                        entries {
                            name
                            type
                            path
                            mode
                            object {
                                ... on Blob {
                                    byteSize
                                    isBinary
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        return query, {"owner": owner, "name": name, "expression": path}
    
    @staticmethod
    def repo_file_content(owner: str, name: str, path: str) -> tuple[str, dict[str, Any]]:
        """Query for file content."""
        query = """
        query RepoFileContent($owner: String!, $name: String!, $expression: String!) {
            repository(owner: $owner, name: $name) {
                object(expression: $expression) {
                    ... on Blob {
                        text
                        byteSize
                        isBinary
                    }
                }
            }
        }
        """
        return query, {"owner": owner, "name": name, "expression": f"HEAD:{path}"}
    
    @staticmethod
    def repo_issues(owner: str, name: str, states: list[str] = None) -> tuple[str, dict[str, Any]]:
        """Query for repository issues."""
        states = states or ["OPEN"]
        query = """
        query RepoIssues($owner: String!, $name: String!, $states: [IssueState!], $first: Int!, $after: String) {
            repository(owner: $owner, name: $name) {
                issues(states: $states, first: $first, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        number
                        title
                        state
                        createdAt
                        updatedAt
                        author { login }
                        labels(first: 10) {
                            nodes { name color }
                        }
                        assignees(first: 5) {
                            nodes { login }
                        }
                    }
                }
            }
        }
        """
        return query, {"owner": owner, "name": name, "states": states, "first": 100}
    
    @staticmethod
    def repo_prs(owner: str, name: str, states: list[str] = None) -> tuple[str, dict[str, Any]]:
        """Query for repository pull requests."""
        states = states or ["OPEN"]
        query = """
        query RepoPRs($owner: String!, $name: String!, $states: [PullRequestState!], $first: Int!, $after: String) {
            repository(owner: $owner, name: $name) {
                pullRequests(states: $states, first: $first, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    totalCount
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        number
                        title
                        state
                        createdAt
                        updatedAt
                        mergedAt
                        author { login }
                        headRefName
                        baseRefName
                        additions
                        deletions
                        changedFiles
                        reviewDecision
                    }
                }
            }
        }
        """
        return query, {"owner": owner, "name": name, "states": states, "first": 100}
