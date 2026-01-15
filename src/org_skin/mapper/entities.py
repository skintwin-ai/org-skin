"""
Entity Models

Data models for GitHub organization entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum


class EntityType(Enum):
    """Types of organization entities."""
    ORGANIZATION = "organization"
    REPOSITORY = "repository"
    TEAM = "team"
    MEMBER = "member"
    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
    PROJECT = "project"
    DISCUSSION = "discussion"
    BRANCH = "branch"
    RELEASE = "release"


@dataclass
class BaseEntity:
    """Base class for all entities."""
    id: str
    node_id: str = ""
    entity_type: EntityType = EntityType.ORGANIZATION
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "id": self.id,
            "node_id": self.node_id,
            "entity_type": self.entity_type.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }


@dataclass
class Organization(BaseEntity):
    """Organization entity."""
    login: str = ""
    name: str = ""
    description: str = ""
    url: str = ""
    avatar_url: str = ""
    website_url: str = ""
    email: str = ""
    is_verified: bool = False
    repo_count: int = 0
    team_count: int = 0
    member_count: int = 0
    
    def __post_init__(self):
        self.entity_type = EntityType.ORGANIZATION
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "login": self.login,
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "avatar_url": self.avatar_url,
            "website_url": self.website_url,
            "email": self.email,
            "is_verified": self.is_verified,
            "repo_count": self.repo_count,
            "team_count": self.team_count,
            "member_count": self.member_count,
        })
        return base


@dataclass
class Repository(BaseEntity):
    """Repository entity."""
    name: str = ""
    full_name: str = ""
    description: str = ""
    url: str = ""
    homepage_url: str = ""
    is_private: bool = False
    is_archived: bool = False
    is_fork: bool = False
    primary_language: str = ""
    default_branch: str = "main"
    disk_usage: int = 0
    stargazer_count: int = 0
    fork_count: int = 0
    open_issues_count: int = 0
    open_prs_count: int = 0
    languages: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    license_name: str = ""
    pushed_at: Optional[datetime] = None
    
    def __post_init__(self):
        self.entity_type = EntityType.REPOSITORY
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "name": self.name,
            "full_name": self.full_name,
            "description": self.description,
            "url": self.url,
            "homepage_url": self.homepage_url,
            "is_private": self.is_private,
            "is_archived": self.is_archived,
            "is_fork": self.is_fork,
            "primary_language": self.primary_language,
            "default_branch": self.default_branch,
            "disk_usage": self.disk_usage,
            "stargazer_count": self.stargazer_count,
            "fork_count": self.fork_count,
            "open_issues_count": self.open_issues_count,
            "open_prs_count": self.open_prs_count,
            "languages": self.languages,
            "topics": self.topics,
            "license_name": self.license_name,
            "pushed_at": self.pushed_at.isoformat() if self.pushed_at else None,
        })
        return base


@dataclass
class Team(BaseEntity):
    """Team entity."""
    name: str = ""
    slug: str = ""
    description: str = ""
    privacy: str = "visible"
    member_count: int = 0
    repo_count: int = 0
    parent_team_id: Optional[str] = None
    
    def __post_init__(self):
        self.entity_type = EntityType.TEAM
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "privacy": self.privacy,
            "member_count": self.member_count,
            "repo_count": self.repo_count,
            "parent_team_id": self.parent_team_id,
        })
        return base


@dataclass
class Member(BaseEntity):
    """Member entity."""
    login: str = ""
    name: str = ""
    email: str = ""
    avatar_url: str = ""
    bio: str = ""
    company: str = ""
    location: str = ""
    role: str = "member"
    
    def __post_init__(self):
        self.entity_type = EntityType.MEMBER
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "login": self.login,
            "name": self.name,
            "email": self.email,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "company": self.company,
            "location": self.location,
            "role": self.role,
        })
        return base


class IssueState(Enum):
    """Issue states."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass
class Issue(BaseEntity):
    """Issue entity."""
    number: int = 0
    title: str = ""
    body: str = ""
    state: IssueState = IssueState.OPEN
    url: str = ""
    author_login: str = ""
    repository_id: str = ""
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    milestone: str = ""
    comment_count: int = 0
    closed_at: Optional[datetime] = None
    
    def __post_init__(self):
        self.entity_type = EntityType.ISSUE
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state.value,
            "url": self.url,
            "author_login": self.author_login,
            "repository_id": self.repository_id,
            "labels": self.labels,
            "assignees": self.assignees,
            "milestone": self.milestone,
            "comment_count": self.comment_count,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
        })
        return base


class PRState(Enum):
    """Pull request states."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"


class ReviewDecision(Enum):
    """Review decision states."""
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NONE = "NONE"


@dataclass
class PullRequest(BaseEntity):
    """Pull request entity."""
    number: int = 0
    title: str = ""
    body: str = ""
    state: PRState = PRState.OPEN
    url: str = ""
    author_login: str = ""
    repository_id: str = ""
    head_ref: str = ""
    base_ref: str = ""
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    review_decision: ReviewDecision = ReviewDecision.NONE
    is_draft: bool = False
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        self.entity_type = EntityType.PULL_REQUEST
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "number": self.number,
            "title": self.title,
            "body": self.body,
            "state": self.state.value,
            "url": self.url,
            "author_login": self.author_login,
            "repository_id": self.repository_id,
            "head_ref": self.head_ref,
            "base_ref": self.base_ref,
            "additions": self.additions,
            "deletions": self.deletions,
            "changed_files": self.changed_files,
            "review_decision": self.review_decision.value,
            "is_draft": self.is_draft,
            "merged_at": self.merged_at.isoformat() if self.merged_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "labels": self.labels,
            "assignees": self.assignees,
            "reviewers": self.reviewers,
        })
        return base


@dataclass
class Project(BaseEntity):
    """Project entity."""
    name: str = ""
    title: str = ""
    description: str = ""
    url: str = ""
    state: str = "open"
    item_count: int = 0
    
    def __post_init__(self):
        self.entity_type = EntityType.PROJECT
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "state": self.state,
            "item_count": self.item_count,
        })
        return base


@dataclass
class Branch(BaseEntity):
    """Branch entity."""
    name: str = ""
    repository_id: str = ""
    commit_sha: str = ""
    is_protected: bool = False
    
    def __post_init__(self):
        self.entity_type = EntityType.BRANCH
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "name": self.name,
            "repository_id": self.repository_id,
            "commit_sha": self.commit_sha,
            "is_protected": self.is_protected,
        })
        return base


@dataclass
class Release(BaseEntity):
    """Release entity."""
    name: str = ""
    tag_name: str = ""
    repository_id: str = ""
    description: str = ""
    url: str = ""
    is_draft: bool = False
    is_prerelease: bool = False
    published_at: Optional[datetime] = None
    
    def __post_init__(self):
        self.entity_type = EntityType.RELEASE
    
    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "name": self.name,
            "tag_name": self.tag_name,
            "repository_id": self.repository_id,
            "description": self.description,
            "url": self.url,
            "is_draft": self.is_draft,
            "is_prerelease": self.is_prerelease,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        })
        return base


# Relationship types
class RelationType(Enum):
    """Types of relationships between entities."""
    OWNS = "owns"  # Organization owns Repository
    MEMBER_OF = "member_of"  # Member is member of Organization/Team
    MAINTAINS = "maintains"  # Team maintains Repository
    AUTHORED = "authored"  # Member authored Issue/PR
    ASSIGNED_TO = "assigned_to"  # Issue/PR assigned to Member
    REVIEWS = "reviews"  # Member reviews PR
    DEPENDS_ON = "depends_on"  # Repository depends on Repository
    FORKED_FROM = "forked_from"  # Repository forked from Repository
    PARENT_OF = "parent_of"  # Team is parent of Team


@dataclass
class Relationship:
    """Represents a relationship between two entities."""
    source_id: str
    target_id: str
    relation_type: RelationType
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "metadata": self.metadata,
        }
