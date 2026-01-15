"""Pytest configuration and fixtures."""

import pytest
import os


@pytest.fixture
def github_token():
    """Get GitHub token from environment."""
    return os.environ.get("GITHUB_TOKEN", "test_token")


@pytest.fixture
def test_org():
    """Test organization name."""
    return "skintwin-ai"


@pytest.fixture
def mock_graphql_response():
    """Mock GraphQL response."""
    return {
        "data": {
            "organization": {
                "login": "skintwin-ai",
                "name": "SkinTwin AI",
                "repositories": {
                    "totalCount": 5,
                    "nodes": [
                        {"name": "org-skin", "description": "Org SDK"},
                        {"name": "test-repo", "description": "Test"},
                    ]
                }
            }
        }
    }
