"""Tests for organization mapper."""

import pytest
from org_skin.mapper.entities import Organization, Repository, Team, Member


class TestEntities:
    """Test entity models."""
    
    def test_organization_creation(self):
        """Test organization entity creation."""
        org = Organization(
            id="org_123",
            login="test-org",
            name="Test Organization",
        )
        assert org.id == "org_123"
        assert org.login == "test-org"
    
    def test_repository_creation(self):
        """Test repository entity creation."""
        repo = Repository(
            id="repo_123",
            name="test-repo",
            full_name="test-org/test-repo",
        )
        assert repo.id == "repo_123"
        assert repo.name == "test-repo"
    
    def test_team_creation(self):
        """Test team entity creation."""
        team = Team(
            id="team_123",
            name="Test Team",
            slug="test-team",
        )
        assert team.id == "team_123"
        assert team.slug == "test-team"
    
    def test_member_creation(self):
        """Test member entity creation."""
        member = Member(
            id="member_123",
            login="testuser",
            name="Test User",
        )
        assert member.id == "member_123"
        assert member.login == "testuser"
