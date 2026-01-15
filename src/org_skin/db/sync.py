"""
Data Synchronization

Synchronizes local data with GitHub and repository files.
"""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import logging
import subprocess

from org_skin.db.store import DataStore
from org_skin.db.models import (
    OrgData, RepoData, EntityData, SyncRecord, SyncStatus
)
from org_skin.graphql.client import GitHubGraphQLClient
from org_skin.mapper.scanner import OrganizationMapper

logger = logging.getLogger(__name__)


@dataclass
class SyncConfig:
    """Configuration for data synchronization."""
    organization: str = "skintwin-ai"
    repository: str = "org-skin"
    branch: str = "main"
    data_path: str = "data"
    auto_commit: bool = True
    commit_message: str = "Sync organization data"


class DataSyncer:
    """
    Synchronizes data between local storage and GitHub.
    
    Features:
    - Pull data from GitHub API
    - Push data to repository
    - Incremental sync
    - Conflict resolution
    - Automatic commits
    """
    
    def __init__(
        self,
        store: DataStore,
        config: Optional[SyncConfig] = None,
        github_token: Optional[str] = None,
    ):
        """
        Initialize the data syncer.
        
        Args:
            store: Data store instance.
            config: Sync configuration.
            github_token: GitHub Personal Access Token.
        """
        self.store = store
        self.config = config or SyncConfig()
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self._client: Optional[GitHubGraphQLClient] = None
        self._mapper: Optional[OrganizationMapper] = None
    
    async def sync_from_github(self) -> SyncRecord:
        """
        Sync data from GitHub API.
        
        Returns:
            SyncRecord with sync results.
        """
        record = SyncRecord(
            id=f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            operation="pull",
            target="github",
            status="in_progress",
            started_at=datetime.now(),
        )
        self.store.sync_records.save(record)
        
        try:
            # Initialize mapper
            if self._client is None:
                self._client = GitHubGraphQLClient(token=self.github_token)
            
            if self._mapper is None:
                self._mapper = OrganizationMapper(self._client)
            
            # Scan organization
            logger.info(f"Scanning organization: {self.config.organization}")
            scan_result = await self._mapper.scan(
                self.config.organization,
                include_issues=True,
                include_prs=True,
            )
            
            # Save organization data
            if scan_result.organization:
                org_data = OrgData(
                    id=scan_result.organization.id,
                    login=scan_result.organization.login,
                    name=scan_result.organization.name,
                    description=scan_result.organization.description,
                    url=scan_result.organization.url,
                    avatar_url=scan_result.organization.avatar_url,
                    repo_count=scan_result.organization.repo_count,
                    team_count=scan_result.organization.team_count,
                    member_count=scan_result.organization.member_count,
                    sync_status=SyncStatus.SYNCED,
                )
                self.store.organizations.save(org_data)
                record.items_created += 1
            
            # Save repositories
            for repo in scan_result.repositories:
                repo_data = RepoData(
                    id=repo.id,
                    org_id=scan_result.organization.id if scan_result.organization else "",
                    name=repo.name,
                    full_name=repo.full_name,
                    description=repo.description,
                    url=repo.url,
                    is_private=repo.is_private,
                    is_archived=repo.is_archived,
                    is_fork=repo.is_fork,
                    primary_language=repo.primary_language,
                    default_branch=repo.default_branch,
                    stargazer_count=repo.stargazer_count,
                    fork_count=repo.fork_count,
                    languages={lang: 1 for lang in repo.languages},
                    topics=repo.topics,
                    pushed_at=repo.pushed_at,
                    sync_status=SyncStatus.SYNCED,
                )
                self.store.repositories.save(repo_data)
                record.items_created += 1
            
            # Save teams
            for team in scan_result.teams:
                entity_data = EntityData(
                    id=team.id,
                    entity_type="team",
                    org_id=scan_result.organization.id if scan_result.organization else "",
                    name=team.name,
                    slug=team.slug,
                    description=team.description,
                    privacy=team.privacy,
                    member_count=team.member_count,
                    sync_status=SyncStatus.SYNCED,
                )
                self.store.entities.save(entity_data)
                record.items_created += 1
            
            # Save members
            for member in scan_result.members:
                entity_data = EntityData(
                    id=member.id,
                    entity_type="member",
                    org_id=scan_result.organization.id if scan_result.organization else "",
                    login=member.login,
                    name=member.name,
                    email=member.email,
                    avatar_url=member.avatar_url,
                    role=member.role,
                    sync_status=SyncStatus.SYNCED,
                )
                self.store.entities.save(entity_data)
                record.items_created += 1
            
            # Save issues
            for issue in scan_result.issues:
                entity_data = EntityData(
                    id=issue.id,
                    entity_type="issue",
                    org_id=scan_result.organization.id if scan_result.organization else "",
                    repo_id=issue.repository_id,
                    number=issue.number,
                    title=issue.title,
                    state=issue.state.value,
                    author=issue.author_login,
                    labels=issue.labels,
                    assignees=issue.assignees,
                    sync_status=SyncStatus.SYNCED,
                )
                self.store.entities.save(entity_data)
                record.items_created += 1
            
            # Save pull requests
            for pr in scan_result.pull_requests:
                entity_data = EntityData(
                    id=pr.id,
                    entity_type="pr",
                    org_id=scan_result.organization.id if scan_result.organization else "",
                    repo_id=pr.repository_id,
                    number=pr.number,
                    title=pr.title,
                    state=pr.state.value,
                    author=pr.author_login,
                    labels=pr.labels,
                    assignees=pr.assignees,
                    extra={
                        "head_ref": pr.head_ref,
                        "base_ref": pr.base_ref,
                        "additions": pr.additions,
                        "deletions": pr.deletions,
                    },
                    sync_status=SyncStatus.SYNCED,
                )
                self.store.entities.save(entity_data)
                record.items_created += 1
            
            record.status = "completed"
            record.items_processed = record.items_created
            
        except Exception as e:
            logger.error(f"Sync from GitHub failed: {e}")
            record.status = "failed"
            record.errors.append(str(e))
        
        record.completed_at = datetime.now()
        self.store.sync_records.save(record)
        
        return record
    
    async def sync_to_repository(self, repo_path: str) -> SyncRecord:
        """
        Sync data to repository files.
        
        Args:
            repo_path: Path to the repository.
            
        Returns:
            SyncRecord with sync results.
        """
        record = SyncRecord(
            id=f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            operation="push",
            target="repository",
            status="in_progress",
            started_at=datetime.now(),
        )
        self.store.sync_records.save(record)
        
        try:
            repo_path = Path(repo_path)
            data_path = repo_path / self.config.data_path
            data_path.mkdir(parents=True, exist_ok=True)
            
            # Export organization data
            orgs = self.store.organizations.get_all()
            if orgs:
                org_file = data_path / "organization.json"
                with open(org_file, 'w') as f:
                    json.dump([o.to_dict() for o in orgs], f, indent=2, default=str)
                record.items_processed += len(orgs)
            
            # Export repository data
            repos = self.store.repositories.get_all()
            if repos:
                repos_file = data_path / "repositories.json"
                with open(repos_file, 'w') as f:
                    json.dump([r.to_dict() for r in repos], f, indent=2, default=str)
                record.items_processed += len(repos)
            
            # Export entities by type
            entities = self.store.entities.get_all()
            entities_by_type: dict[str, list] = {}
            for entity in entities:
                entity_type = entity.entity_type
                if entity_type not in entities_by_type:
                    entities_by_type[entity_type] = []
                entities_by_type[entity_type].append(entity.to_dict())
            
            for entity_type, entity_list in entities_by_type.items():
                entity_file = data_path / f"{entity_type}s.json"
                with open(entity_file, 'w') as f:
                    json.dump(entity_list, f, indent=2, default=str)
                record.items_processed += len(entity_list)
            
            # Export patterns
            patterns = self.store.patterns.get_all()
            if patterns:
                patterns_file = data_path / "patterns.json"
                with open(patterns_file, 'w') as f:
                    json.dump([p.to_dict() for p in patterns], f, indent=2, default=str)
                record.items_processed += len(patterns)
            
            # Export analyses
            analyses = self.store.analyses.get_all()
            if analyses:
                analyses_file = data_path / "analyses.json"
                with open(analyses_file, 'w') as f:
                    json.dump([a.to_dict() for a in analyses], f, indent=2, default=str)
                record.items_processed += len(analyses)
            
            # Create summary file
            summary = {
                "organization": self.config.organization,
                "synced_at": datetime.now().isoformat(),
                "stats": self.store.get_stats(),
            }
            summary_file = data_path / "summary.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            # Auto commit if enabled
            if self.config.auto_commit:
                await self._git_commit(repo_path)
            
            record.status = "completed"
            
        except Exception as e:
            logger.error(f"Sync to repository failed: {e}")
            record.status = "failed"
            record.errors.append(str(e))
        
        record.completed_at = datetime.now()
        self.store.sync_records.save(record)
        
        return record
    
    async def _git_commit(self, repo_path: Path) -> None:
        """Commit changes to git."""
        try:
            # Add all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            
            # Check if there are changes to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            
            if result.stdout.strip():
                # Commit changes
                subprocess.run(
                    ["git", "commit", "-m", self.config.commit_message],
                    cwd=repo_path,
                    check=True,
                    capture_output=True,
                )
                logger.info("Changes committed to git")
            else:
                logger.info("No changes to commit")
                
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git commit failed: {e}")
    
    async def push_to_github(self, repo_path: str) -> bool:
        """
        Push changes to GitHub.
        
        Args:
            repo_path: Path to the repository.
            
        Returns:
            True if successful.
        """
        try:
            subprocess.run(
                ["git", "push", "origin", self.config.branch],
                cwd=repo_path,
                check=True,
                capture_output=True,
            )
            logger.info("Changes pushed to GitHub")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Git push failed: {e}")
            return False
    
    async def full_sync(self, repo_path: str) -> tuple[SyncRecord, SyncRecord]:
        """
        Perform full sync: pull from GitHub and push to repository.
        
        Args:
            repo_path: Path to the repository.
            
        Returns:
            Tuple of (pull_record, push_record).
        """
        # Pull from GitHub
        pull_record = await self.sync_from_github()
        
        # Push to repository
        push_record = await self.sync_to_repository(repo_path)
        
        # Push to GitHub
        if push_record.status == "completed":
            await self.push_to_github(repo_path)
        
        return pull_record, push_record
    
    def get_sync_history(self, limit: int = 10) -> list[SyncRecord]:
        """Get recent sync history."""
        records = self.store.sync_records.get_all()
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]
    
    def get_pending_changes(self) -> dict[str, int]:
        """Get count of pending changes by collection."""
        pending = {}
        
        for collection_name in ["organizations", "repositories", "entities", "patterns", "analyses"]:
            collection = getattr(self.store, collection_name)
            items = collection.find(sync_status=SyncStatus.MODIFIED)
            if items:
                pending[collection_name] = len(items)
        
        return pending
