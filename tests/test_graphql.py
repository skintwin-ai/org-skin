"""Tests for GraphQL client."""

import pytest
from org_skin.graphql.client import GitHubGraphQLClient, GraphQLResult


class TestGraphQLClient:
    """Test GraphQL client functionality."""
    
    def test_client_initialization(self, github_token):
        """Test client can be initialized."""
        client = GitHubGraphQLClient(token=github_token)
        assert client is not None
        assert client.token == github_token
    
    def test_graphql_result_success(self):
        """Test successful GraphQL result."""
        result = GraphQLResult(
            success=True,
            data={"test": "data"},
            errors=None,
        )
        assert result.success
        assert result.data == {"test": "data"}
        assert result.errors is None
    
    def test_graphql_result_failure(self):
        """Test failed GraphQL result."""
        result = GraphQLResult(
            success=False,
            data=None,
            errors=[{"message": "Error"}],
        )
        assert not result.success
        assert result.data is None
        assert len(result.errors) == 1
