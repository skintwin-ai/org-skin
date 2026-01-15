"""
Database Models

Data models for persistent storage of organization data.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional
from enum import Enum
import hashlib


class SyncStatus(Enum):
    """Synchronization status."""
    PENDING = "pending"
    SYNCED = "synced"
    MODIFIED = "modified"
    DELETED = "deleted"
    ERROR = "error"


@dataclass
class BaseData:
    """Base class for all data models."""
    id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    sync_status: SyncStatus = SyncStatus.PENDING
    version: int = 1
    checksum: str = ""
    
    def compute_checksum(self) -> str:
        """Compute checksum of the data."""
        data = self.to_dict()
        data.pop("checksum", None)
        data.pop("sync_status", None)
        data.pop("updated_at", None)
        
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["created_at"] = self.created_at.isoformat()
        result["updated_at"] = self.updated_at.isoformat()
        result["sync_status"] = self.sync_status.value
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseData":
        """Create from dictionary."""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        data["sync_status"] = SyncStatus(data["sync_status"])
        return cls(**data)


@dataclass
class OrgData(BaseData):
    """Organization data model."""
    login: str = ""
    name: str = ""
    description: str = ""
    url: str = ""
    avatar_url: str = ""
    repo_count: int = 0
    team_count: int = 0
    member_count: int = 0
    
    # Aggregated metrics
    total_stars: int = 0
    total_forks: int = 0
    total_issues: int = 0
    total_prs: int = 0
    
    # Analysis data
    primary_languages: list[str] = field(default_factory=list)
    tech_stack: dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        return result


@dataclass
class RepoData(BaseData):
    """Repository data model."""
    org_id: str = ""
    name: str = ""
    full_name: str = ""
    description: str = ""
    url: str = ""
    
    # Metadata
    is_private: bool = False
    is_archived: bool = False
    is_fork: bool = False
    primary_language: str = ""
    default_branch: str = "main"
    
    # Metrics
    stargazer_count: int = 0
    fork_count: int = 0
    open_issues_count: int = 0
    open_prs_count: int = 0
    disk_usage: int = 0
    
    # Analysis
    languages: dict[str, int] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    dependencies: list[dict[str, Any]] = field(default_factory=list)
    
    # Documentation
    has_readme: bool = False
    has_contributing: bool = False
    has_license: bool = False
    license_name: str = ""
    
    # CI/CD
    has_ci: bool = False
    ci_platforms: list[str] = field(default_factory=list)
    
    # Testing
    has_tests: bool = False
    test_frameworks: list[str] = field(default_factory=list)
    
    # Quality
    quality_score: float = 0.0
    maintainability_score: float = 0.0
    
    # Timestamps
    pushed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        if self.pushed_at:
            result["pushed_at"] = self.pushed_at.isoformat()
        return result


@dataclass
class EntityData(BaseData):
    """Generic entity data model for issues, PRs, teams, members."""
    entity_type: str = ""  # 'issue', 'pr', 'team', 'member'
    org_id: str = ""
    repo_id: Optional[str] = None
    
    # Common fields
    name: str = ""
    title: str = ""
    description: str = ""
    url: str = ""
    state: str = ""
    
    # Issue/PR specific
    number: Optional[int] = None
    author: str = ""
    labels: list[str] = field(default_factory=list)
    assignees: list[str] = field(default_factory=list)
    
    # Team specific
    slug: str = ""
    privacy: str = ""
    member_count: int = 0
    
    # Member specific
    login: str = ""
    email: str = ""
    role: str = ""
    avatar_url: str = ""
    
    # Additional data
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowData(BaseData):
    """Workflow data model for AIML workflows."""
    name: str = ""
    description: str = ""
    trigger: str = ""  # 'manual', 'scheduled', 'event'
    
    # Workflow definition
    steps: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    
    # Execution history
    last_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    # AIML pattern
    aiml_pattern: str = ""
    aiml_template: str = ""


@dataclass
class PatternData(BaseData):
    """AIML pattern data model."""
    pattern: str = ""
    template: str = ""
    category: str = ""
    
    # Usage tracking
    match_count: int = 0
    last_matched: Optional[datetime] = None
    
    # Learning data
    confidence: float = 1.0
    source: str = ""  # 'predefined', 'learned', 'user'
    
    # GraphQL mapping
    graphql_query: str = ""
    graphql_variables: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisData(BaseData):
    """Analysis result data model."""
    analysis_type: str = ""  # 'repo', 'org', 'combined'
    target_id: str = ""
    
    # Results
    features: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    
    # Recommendations
    best_practices: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    
    # Metadata
    scan_time: float = 0.0
    entity_count: int = 0


@dataclass
class SyncRecord(BaseData):
    """Record of synchronization operations."""
    operation: str = ""  # 'push', 'pull', 'sync'
    target: str = ""  # 'github', 'local', 'both'
    
    # Status
    status: str = "pending"  # 'pending', 'in_progress', 'completed', 'failed'
    progress: float = 0.0
    
    # Results
    items_processed: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_deleted: int = 0
    items_failed: int = 0
    
    # Errors
    errors: list[str] = field(default_factory=list)
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Index definitions for efficient querying
INDEXES = {
    "org_data": ["login", "name"],
    "repo_data": ["org_id", "name", "full_name", "primary_language"],
    "entity_data": ["entity_type", "org_id", "repo_id", "state"],
    "workflow_data": ["name", "trigger"],
    "pattern_data": ["pattern", "category"],
    "analysis_data": ["analysis_type", "target_id"],
    "sync_record": ["operation", "status"],
}
