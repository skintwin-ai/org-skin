"""
Organization Scanner

Discovers and maps all entities in a GitHub organization.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import logging

from org_skin.graphql.client import GitHubGraphQLClient
from org_skin.graphql.queries import OrgQueries, RepoQueries
from org_skin.mapper.entities import (
    Organization, Repository, Team, Member, Issue, PullRequest,
    Project, Branch, Release, Relationship, RelationType,
    IssueState, PRState, ReviewDecision
)
from org_skin.mapper.graph import OrgGraph

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of an organization scan."""
    organization: Optional[Organization] = None
    repositories: list[Repository] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    pull_requests: list[PullRequest] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    scan_time: float = 0.0
    errors: list[str] = field(default_factory=list)
    
    @property
    def total_entities(self) -> int:
        return (
            (1 if self.organization else 0) +
            len(self.repositories) +
            len(self.teams) +
            len(self.members) +
            len(self.issues) +
            len(self.pull_requests) +
            len(self.projects)
        )


class OrganizationMapper:
    """
    Maps an entire GitHub organization.
    
    Features:
    - Discovers all repositories, teams, and members
    - Extracts issues and pull requests
    - Builds relationship graph
    - Supports incremental updates
    """
    
    def __init__(self, client: Optional[GitHubGraphQLClient] = None):
        """
        Initialize the organization mapper.
        
        Args:
            client: GitHub GraphQL client. If not provided, creates a new one.
        """
        self.client = client
        self.graph = OrgGraph()
        self._scan_result: Optional[ScanResult] = None
    
    async def scan(
        self,
        org_login: str,
        include_issues: bool = True,
        include_prs: bool = True,
        include_projects: bool = False,
        max_repos: Optional[int] = None,
    ) -> ScanResult:
        """
        Scan an organization and map all entities.
        
        Args:
            org_login: Organization login name.
            include_issues: Whether to scan issues.
            include_prs: Whether to scan pull requests.
            include_projects: Whether to scan projects.
            max_repos: Maximum number of repositories to scan.
            
        Returns:
            ScanResult with all discovered entities.
        """
        import time
        start_time = time.time()
        
        result = ScanResult()
        
        # Create client if not provided
        if self.client is None:
            self.client = GitHubGraphQLClient()
        
        async with self.client:
            # Scan organization overview
            logger.info(f"Scanning organization: {org_login}")
            org = await self._scan_organization(org_login)
            if org:
                result.organization = org
                self.graph.add_entity(org)
            else:
                result.errors.append(f"Failed to scan organization: {org_login}")
                return result
            
            # Scan repositories
            logger.info("Scanning repositories...")
            repos = await self._scan_repositories(org_login, max_repos)
            result.repositories = repos
            for repo in repos:
                self.graph.add_entity(repo)
                result.relationships.append(Relationship(
                    source_id=org.id,
                    target_id=repo.id,
                    relation_type=RelationType.OWNS,
                ))
            
            # Scan teams
            logger.info("Scanning teams...")
            teams = await self._scan_teams(org_login)
            result.teams = teams
            for team in teams:
                self.graph.add_entity(team)
            
            # Scan members
            logger.info("Scanning members...")
            members = await self._scan_members(org_login)
            result.members = members
            for member in members:
                self.graph.add_entity(member)
                result.relationships.append(Relationship(
                    source_id=member.id,
                    target_id=org.id,
                    relation_type=RelationType.MEMBER_OF,
                ))
            
            # Scan issues and PRs for each repository
            if include_issues or include_prs:
                for repo in repos[:10]:  # Limit to first 10 repos for performance
                    if include_issues:
                        logger.info(f"Scanning issues for {repo.name}...")
                        issues = await self._scan_issues(org_login, repo.name)
                        result.issues.extend(issues)
                        for issue in issues:
                            self.graph.add_entity(issue)
                    
                    if include_prs:
                        logger.info(f"Scanning PRs for {repo.name}...")
                        prs = await self._scan_pull_requests(org_login, repo.name)
                        result.pull_requests.extend(prs)
                        for pr in prs:
                            self.graph.add_entity(pr)
            
            # Build relationships
            for rel in result.relationships:
                self.graph.add_relationship(rel)
        
        result.scan_time = time.time() - start_time
        self._scan_result = result
        
        logger.info(f"Scan complete: {result.total_entities} entities in {result.scan_time:.2f}s")
        return result
    
    async def _scan_organization(self, org_login: str) -> Optional[Organization]:
        """Scan organization overview."""
        query, variables = OrgQueries.org_overview(org_login)
        result = await self.client.execute(query, variables)
        
        if not result.success or not result.data.get("organization"):
            return None
        
        org_data = result.data["organization"]
        return Organization(
            id=org_data.get("id", ""),
            node_id=org_data.get("id", ""),
            login=org_data.get("login", ""),
            name=org_data.get("name", ""),
            description=org_data.get("description", ""),
            url=org_data.get("url", ""),
            avatar_url=org_data.get("avatarUrl", ""),
            website_url=org_data.get("websiteUrl", ""),
            email=org_data.get("email", ""),
            is_verified=org_data.get("isVerified", False),
            repo_count=org_data.get("repositories", {}).get("totalCount", 0),
            team_count=org_data.get("teams", {}).get("totalCount", 0),
            member_count=org_data.get("membersWithRole", {}).get("totalCount", 0),
            created_at=self._parse_datetime(org_data.get("createdAt")),
        )
    
    async def _scan_repositories(
        self,
        org_login: str,
        max_repos: Optional[int] = None,
    ) -> list[Repository]:
        """Scan organization repositories."""
        query, variables = OrgQueries.list_repos(org_login)
        
        repos_data = await self.client.paginate(
            query,
            variables,
            path=["organization", "repositories"],
            max_pages=max_repos // 100 + 1 if max_repos else None,
        )
        
        repositories = []
        for repo_data in repos_data[:max_repos] if max_repos else repos_data:
            repo = Repository(
                id=repo_data.get("id", ""),
                node_id=repo_data.get("id", ""),
                name=repo_data.get("name", ""),
                full_name=repo_data.get("nameWithOwner", ""),
                description=repo_data.get("description", "") or "",
                url=repo_data.get("url", ""),
                homepage_url=repo_data.get("homepageUrl", "") or "",
                is_private=repo_data.get("isPrivate", False),
                is_archived=repo_data.get("isArchived", False),
                is_fork=repo_data.get("isFork", False),
                primary_language=repo_data.get("primaryLanguage", {}).get("name", "") if repo_data.get("primaryLanguage") else "",
                default_branch=repo_data.get("defaultBranchRef", {}).get("name", "main") if repo_data.get("defaultBranchRef") else "main",
                disk_usage=repo_data.get("diskUsage", 0),
                stargazer_count=repo_data.get("stargazerCount", 0),
                fork_count=repo_data.get("forkCount", 0),
                languages=[lang.get("name", "") for lang in repo_data.get("languages", {}).get("nodes", [])],
                topics=[topic.get("topic", {}).get("name", "") for topic in repo_data.get("repositoryTopics", {}).get("nodes", [])],
                created_at=self._parse_datetime(repo_data.get("createdAt")),
                updated_at=self._parse_datetime(repo_data.get("updatedAt")),
                pushed_at=self._parse_datetime(repo_data.get("pushedAt")),
            )
            repositories.append(repo)
        
        return repositories
    
    async def _scan_teams(self, org_login: str) -> list[Team]:
        """Scan organization teams."""
        query, variables = OrgQueries.list_teams(org_login)
        
        teams_data = await self.client.paginate(
            query,
            variables,
            path=["organization", "teams"],
        )
        
        teams = []
        for team_data in teams_data:
            team = Team(
                id=team_data.get("id", ""),
                node_id=team_data.get("id", ""),
                name=team_data.get("name", ""),
                slug=team_data.get("slug", ""),
                description=team_data.get("description", "") or "",
                privacy=team_data.get("privacy", "visible"),
                member_count=team_data.get("membersCount", {}).get("totalCount", 0),
                repo_count=team_data.get("reposCount", {}).get("totalCount", 0),
            )
            teams.append(team)
        
        return teams
    
    async def _scan_members(self, org_login: str) -> list[Member]:
        """Scan organization members."""
        query, variables = OrgQueries.list_members(org_login)
        
        members_data = await self.client.paginate(
            query,
            variables,
            path=["organization", "membersWithRole"],
        )
        
        members = []
        for member_data in members_data:
            member = Member(
                id=member_data.get("id", ""),
                node_id=member_data.get("id", ""),
                login=member_data.get("login", ""),
                name=member_data.get("name", "") or "",
                email=member_data.get("email", "") or "",
                avatar_url=member_data.get("avatarUrl", ""),
                bio=member_data.get("bio", "") or "",
                company=member_data.get("company", "") or "",
                location=member_data.get("location", "") or "",
            )
            members.append(member)
        
        return members
    
    async def _scan_issues(
        self,
        owner: str,
        repo_name: str,
        states: list[str] = None,
    ) -> list[Issue]:
        """Scan repository issues."""
        query, variables = RepoQueries.repo_issues(owner, repo_name, states or ["OPEN"])
        result = await self.client.execute(query, variables)
        
        if not result.success:
            return []
        
        issues_data = result.data.get("repository", {}).get("issues", {}).get("nodes", [])
        
        issues = []
        for issue_data in issues_data:
            issue = Issue(
                id=issue_data.get("id", ""),
                node_id=issue_data.get("id", ""),
                number=issue_data.get("number", 0),
                title=issue_data.get("title", ""),
                state=IssueState[issue_data.get("state", "OPEN")],
                author_login=issue_data.get("author", {}).get("login", "") if issue_data.get("author") else "",
                labels=[label.get("name", "") for label in issue_data.get("labels", {}).get("nodes", [])],
                assignees=[assignee.get("login", "") for assignee in issue_data.get("assignees", {}).get("nodes", [])],
                created_at=self._parse_datetime(issue_data.get("createdAt")),
                updated_at=self._parse_datetime(issue_data.get("updatedAt")),
            )
            issues.append(issue)
        
        return issues
    
    async def _scan_pull_requests(
        self,
        owner: str,
        repo_name: str,
        states: list[str] = None,
    ) -> list[PullRequest]:
        """Scan repository pull requests."""
        query, variables = RepoQueries.repo_prs(owner, repo_name, states or ["OPEN"])
        result = await self.client.execute(query, variables)
        
        if not result.success:
            return []
        
        prs_data = result.data.get("repository", {}).get("pullRequests", {}).get("nodes", [])
        
        prs = []
        for pr_data in prs_data:
            pr = PullRequest(
                id=pr_data.get("id", ""),
                node_id=pr_data.get("id", ""),
                number=pr_data.get("number", 0),
                title=pr_data.get("title", ""),
                state=PRState[pr_data.get("state", "OPEN")],
                author_login=pr_data.get("author", {}).get("login", "") if pr_data.get("author") else "",
                head_ref=pr_data.get("headRefName", ""),
                base_ref=pr_data.get("baseRefName", ""),
                additions=pr_data.get("additions", 0),
                deletions=pr_data.get("deletions", 0),
                changed_files=pr_data.get("changedFiles", 0),
                review_decision=ReviewDecision[pr_data.get("reviewDecision", "NONE")] if pr_data.get("reviewDecision") else ReviewDecision.NONE,
                created_at=self._parse_datetime(pr_data.get("createdAt")),
                updated_at=self._parse_datetime(pr_data.get("updatedAt")),
                merged_at=self._parse_datetime(pr_data.get("mergedAt")),
            )
            prs.append(pr)
        
        return prs
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except ValueError:
            return None
    
    def get_graph(self) -> OrgGraph:
        """Get the organization graph."""
        return self.graph
    
    def get_scan_result(self) -> Optional[ScanResult]:
        """Get the last scan result."""
        return self._scan_result
    
    def export_to_json(self, filepath: str) -> None:
        """Export scan result to JSON file."""
        import json
        
        if not self._scan_result:
            raise ValueError("No scan result available. Run scan() first.")
        
        data = {
            "organization": self._scan_result.organization.to_dict() if self._scan_result.organization else None,
            "repositories": [r.to_dict() for r in self._scan_result.repositories],
            "teams": [t.to_dict() for t in self._scan_result.teams],
            "members": [m.to_dict() for m in self._scan_result.members],
            "issues": [i.to_dict() for i in self._scan_result.issues],
            "pull_requests": [p.to_dict() for p in self._scan_result.pull_requests],
            "relationships": [r.to_dict() for r in self._scan_result.relationships],
            "scan_time": self._scan_result.scan_time,
            "total_entities": self._scan_result.total_entities,
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
