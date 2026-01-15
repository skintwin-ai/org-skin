"""
Org-Skin SDK: GitHub API GraphQL workflows with AI/ML

A comprehensive platform for building GitHub API GraphQL workflows with AI/ML capabilities.
Serves as the central nervous system for the SkinTwin-AI organization.
"""

__version__ = "0.1.0"
__author__ = "SkinTwin AI"

from org_skin.graphql.client import GitHubGraphQLClient
from org_skin.aiml.encoder import AIMLEncoder
from org_skin.mapper.scanner import OrganizationMapper
from org_skin.chatbot.bot import OrgSkinBot
from org_skin.aggregator.analyzer import FeatureAggregator

__all__ = [
    "GitHubGraphQLClient",
    "AIMLEncoder", 
    "OrganizationMapper",
    "OrgSkinBot",
    "FeatureAggregator",
]
