"""
GraphQL Mutation Builder

Dynamic mutation construction for GitHub GraphQL API.
Supports building complex mutations for repository operations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class MutationInput:
    """Represents an input object for a mutation."""
    fields: dict[str, Any] = field(default_factory=dict)
    
    def to_graphql(self) -> str:
        """Convert input to GraphQL string."""
        items = []
        for k, v in self.fields.items():
            items.append(f"{k}: {self._format_value(v)}")
        return f"{{{', '.join(items)}}}"
    
    def _format_value(self, value: Any) -> str:
        """Format a value for GraphQL."""
        if isinstance(value, str):
            if value.startswith("$"):
                return value
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


class MutationBuilder:
    """
    Dynamic GraphQL mutation builder.
    
    Example:
        builder = MutationBuilder("CreateIssue")
        builder.add_variable("input", "CreateIssueInput!")
        builder.set_mutation("createIssue", {"input": "$input"})
        builder.add_return_field("issue", ["number", "title", "url"])
        mutation = builder.build()
    """
    
    def __init__(self, name: str = "Mutation"):
        """Initialize mutation builder."""
        self.name = name
        self.variables: list[tuple[str, str, Optional[Any]]] = []
        self.mutation_name: str = ""
        self.mutation_args: dict[str, Any] = {}
        self.return_fields: list[tuple[str, list[str]]] = []
    
    def add_variable(
        self,
        name: str,
        type: str,
        default: Optional[Any] = None,
    ) -> "MutationBuilder":
        """Add a variable to the mutation."""
        self.variables.append((name, type, default))
        return self
    
    def set_mutation(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> "MutationBuilder":
        """Set the mutation operation."""
        self.mutation_name = name
        self.mutation_args = arguments
        return self
    
    def add_return_field(
        self,
        name: str,
        fields: list[str],
    ) -> "MutationBuilder":
        """Add return fields to the mutation."""
        self.return_fields.append((name, fields))
        return self
    
    def build(self) -> str:
        """Build the GraphQL mutation string."""
        # Build variable declarations
        var_str = ""
        if self.variables:
            vars_list = []
            for name, type_, default in self.variables:
                var = f"${name}: {type_}"
                if default is not None:
                    var += f" = {self._format_value(default)}"
                vars_list.append(var)
            var_str = f"({', '.join(vars_list)})"
        
        # Build mutation arguments
        args_str = ""
        if self.mutation_args:
            args = ", ".join(
                f"{k}: {v}" if v.startswith("$") else f"{k}: {self._format_value(v)}"
                for k, v in self.mutation_args.items()
            )
            args_str = f"({args})"
        
        # Build return fields
        return_str = ""
        if self.return_fields:
            fields_list = []
            for field_name, subfields in self.return_fields:
                if subfields:
                    subfields_str = " ".join(subfields)
                    fields_list.append(f"{field_name} {{ {subfields_str} }}")
                else:
                    fields_list.append(field_name)
            return_str = " ".join(fields_list)
        
        return f"mutation {self.name}{var_str} {{\n  {self.mutation_name}{args_str} {{\n    {return_str}\n  }}\n}}"
    
    def _format_value(self, value: Any) -> str:
        """Format a value for GraphQL."""
        if isinstance(value, str):
            return f'"{value}"'
        elif isinstance(value, bool):
            return str(value).lower()
        return str(value)
    
    def __str__(self) -> str:
        return self.build()


class RepoMutations:
    """Repository-related mutation templates."""
    
    @staticmethod
    def create_issue(
        repo_id: str,
        title: str,
        body: str = "",
        label_ids: list[str] = None,
        assignee_ids: list[str] = None,
    ) -> tuple[str, dict[str, Any]]:
        """Mutation to create an issue."""
        mutation = """
        mutation CreateIssue($input: CreateIssueInput!) {
            createIssue(input: $input) {
                issue {
                    id
                    number
                    title
                    url
                    state
                }
            }
        }
        """
        input_data = {
            "repositoryId": repo_id,
            "title": title,
            "body": body,
        }
        if label_ids:
            input_data["labelIds"] = label_ids
        if assignee_ids:
            input_data["assigneeIds"] = assignee_ids
        
        return mutation, {"input": input_data}
    
    @staticmethod
    def update_issue(
        issue_id: str,
        title: str = None,
        body: str = None,
        state: str = None,
    ) -> tuple[str, dict[str, Any]]:
        """Mutation to update an issue."""
        mutation = """
        mutation UpdateIssue($input: UpdateIssueInput!) {
            updateIssue(input: $input) {
                issue {
                    id
                    number
                    title
                    state
                    url
                }
            }
        }
        """
        input_data = {"id": issue_id}
        if title:
            input_data["title"] = title
        if body:
            input_data["body"] = body
        if state:
            input_data["state"] = state
        
        return mutation, {"input": input_data}
    
    @staticmethod
    def close_issue(issue_id: str) -> tuple[str, dict[str, Any]]:
        """Mutation to close an issue."""
        return RepoMutations.update_issue(issue_id, state="CLOSED")
    
    @staticmethod
    def add_comment(subject_id: str, body: str) -> tuple[str, dict[str, Any]]:
        """Mutation to add a comment to an issue or PR."""
        mutation = """
        mutation AddComment($input: AddCommentInput!) {
            addComment(input: $input) {
                commentEdge {
                    node {
                        id
                        body
                        createdAt
                        author { login }
                    }
                }
            }
        }
        """
        return mutation, {"input": {"subjectId": subject_id, "body": body}}
    
    @staticmethod
    def add_labels(labelable_id: str, label_ids: list[str]) -> tuple[str, dict[str, Any]]:
        """Mutation to add labels to an issue or PR."""
        mutation = """
        mutation AddLabels($input: AddLabelsToLabelableInput!) {
            addLabelsToLabelable(input: $input) {
                labelable {
                    ... on Issue {
                        id
                        labels(first: 10) {
                            nodes { name color }
                        }
                    }
                    ... on PullRequest {
                        id
                        labels(first: 10) {
                            nodes { name color }
                        }
                    }
                }
            }
        }
        """
        return mutation, {"input": {"labelableId": labelable_id, "labelIds": label_ids}}
    
    @staticmethod
    def create_branch(repo_id: str, name: str, oid: str) -> tuple[str, dict[str, Any]]:
        """Mutation to create a branch."""
        mutation = """
        mutation CreateBranch($input: CreateRefInput!) {
            createRef(input: $input) {
                ref {
                    id
                    name
                    prefix
                }
            }
        }
        """
        return mutation, {
            "input": {
                "repositoryId": repo_id,
                "name": f"refs/heads/{name}",
                "oid": oid,
            }
        }
    
    @staticmethod
    def create_pull_request(
        repo_id: str,
        title: str,
        body: str,
        head_ref: str,
        base_ref: str = "main",
        draft: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """Mutation to create a pull request."""
        mutation = """
        mutation CreatePullRequest($input: CreatePullRequestInput!) {
            createPullRequest(input: $input) {
                pullRequest {
                    id
                    number
                    title
                    url
                    state
                }
            }
        }
        """
        return mutation, {
            "input": {
                "repositoryId": repo_id,
                "title": title,
                "body": body,
                "headRefName": head_ref,
                "baseRefName": base_ref,
                "draft": draft,
            }
        }
    
    @staticmethod
    def merge_pull_request(
        pr_id: str,
        commit_headline: str = None,
        commit_body: str = None,
        merge_method: str = "SQUASH",
    ) -> tuple[str, dict[str, Any]]:
        """Mutation to merge a pull request."""
        mutation = """
        mutation MergePullRequest($input: MergePullRequestInput!) {
            mergePullRequest(input: $input) {
                pullRequest {
                    id
                    number
                    state
                    merged
                    mergedAt
                }
            }
        }
        """
        input_data = {
            "pullRequestId": pr_id,
            "mergeMethod": merge_method,
        }
        if commit_headline:
            input_data["commitHeadline"] = commit_headline
        if commit_body:
            input_data["commitBody"] = commit_body
        
        return mutation, {"input": input_data}


class ProjectMutations:
    """Project-related mutation templates."""
    
    @staticmethod
    def create_project_v2(
        owner_id: str,
        title: str,
    ) -> tuple[str, dict[str, Any]]:
        """Mutation to create a ProjectV2."""
        mutation = """
        mutation CreateProjectV2($input: CreateProjectV2Input!) {
            createProjectV2(input: $input) {
                projectV2 {
                    id
                    title
                    url
                }
            }
        }
        """
        return mutation, {"input": {"ownerId": owner_id, "title": title}}
    
    @staticmethod
    def add_item_to_project(
        project_id: str,
        content_id: str,
    ) -> tuple[str, dict[str, Any]]:
        """Mutation to add an item to a project."""
        mutation = """
        mutation AddProjectItem($input: AddProjectV2ItemByIdInput!) {
            addProjectV2ItemById(input: $input) {
                item {
                    id
                }
            }
        }
        """
        return mutation, {
            "input": {
                "projectId": project_id,
                "contentId": content_id,
            }
        }
