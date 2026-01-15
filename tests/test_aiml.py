"""Tests for AIML encoder."""

import pytest
from org_skin.aiml.encoder import AIMLEncoder, Intent


class TestAIMLEncoder:
    """Test AIML encoder functionality."""
    
    def test_encoder_initialization(self):
        """Test encoder can be initialized."""
        encoder = AIMLEncoder()
        assert encoder is not None
    
    def test_parse_list_repos_intent(self):
        """Test parsing list repos intent."""
        encoder = AIMLEncoder()
        intent = encoder.parse_intent("list all repositories")
        
        assert intent is not None
        assert intent.action == "list"
        assert "repositories" in intent.entity
    
    def test_parse_get_repo_intent(self):
        """Test parsing get repo intent."""
        encoder = AIMLEncoder()
        intent = encoder.parse_intent("get repository org-skin")
        
        assert intent is not None
        assert intent.action == "get"
        assert intent.entity == "repository"
    
    def test_encode_to_graphql(self):
        """Test encoding intent to GraphQL."""
        encoder = AIMLEncoder()
        intent = Intent(
            action="list",
            entity="repositories",
            parameters={"org": "skintwin-ai"},
        )
        
        query = encoder.encode_to_graphql(intent)
        assert query is not None
        assert "repositories" in query.lower()
