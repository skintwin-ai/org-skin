"""
GitHub GraphQL Client

Core client for interacting with GitHub's GraphQL API v4.
Handles authentication, rate limiting, caching, and query execution.
"""

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional
import logging

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RateLimitInfo(BaseModel):
    """GitHub API rate limit information."""
    limit: int = 5000
    remaining: int = 5000
    reset_at: int = 0
    used: int = 0


@dataclass
class QueryResult:
    """Result of a GraphQL query execution."""
    data: dict[str, Any]
    errors: list[dict[str, Any]] = field(default_factory=list)
    rate_limit: Optional[RateLimitInfo] = None
    execution_time: float = 0.0
    
    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class GitHubGraphQLClient:
    """
    Async GitHub GraphQL API client.
    
    Features:
    - Automatic rate limit handling
    - Query caching
    - Retry with exponential backoff
    - Pagination support
    """
    
    GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
    
    def __init__(
        self,
        token: Optional[str] = None,
        cache_ttl: int = 300,
        max_retries: int = 3,
    ):
        """
        Initialize the GitHub GraphQL client.
        
        Args:
            token: GitHub Personal Access Token. If not provided, reads from GITHUB_TOKEN env var.
            cache_ttl: Cache time-to-live in seconds.
            max_retries: Maximum number of retry attempts for failed requests.
        """
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("beast")
        if not self.token:
            raise ValueError("GitHub token is required. Set GITHUB_TOKEN environment variable.")
        
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self._cache: dict[str, tuple[Any, float]] = {}
        self._rate_limit = RateLimitInfo()
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> "GitHubGraphQLClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _get_cache_key(self, query: str, variables: dict[str, Any]) -> str:
        """Generate a cache key for a query."""
        import hashlib
        import json
        content = f"{query}:{json.dumps(variables, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _check_cache(self, key: str) -> Optional[dict[str, Any]]:
        """Check if a cached result exists and is valid."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
            del self._cache[key]
        return None
    
    def _update_cache(self, key: str, data: dict[str, Any]) -> None:
        """Update the cache with new data."""
        self._cache[key] = (data, time.time())
    
    async def _wait_for_rate_limit(self) -> None:
        """Wait if rate limit is exhausted."""
        if self._rate_limit.remaining <= 0:
            wait_time = max(0, self._rate_limit.reset_at - int(time.time()))
            if wait_time > 0:
                logger.warning(f"Rate limit exhausted. Waiting {wait_time} seconds.")
                await asyncio.sleep(wait_time)
    
    def _update_rate_limit(self, headers: httpx.Headers) -> None:
        """Update rate limit info from response headers."""
        if "x-ratelimit-limit" in headers:
            self._rate_limit = RateLimitInfo(
                limit=int(headers.get("x-ratelimit-limit", 5000)),
                remaining=int(headers.get("x-ratelimit-remaining", 5000)),
                reset_at=int(headers.get("x-ratelimit-reset", 0)),
                used=int(headers.get("x-ratelimit-used", 0)),
            )
    
    async def execute(
        self,
        query: str,
        variables: Optional[dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> QueryResult:
        """
        Execute a GraphQL query.
        
        Args:
            query: GraphQL query string.
            variables: Query variables.
            use_cache: Whether to use caching.
            
        Returns:
            QueryResult with data, errors, and metadata.
        """
        variables = variables or {}
        
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(query, variables)
            cached = self._check_cache(cache_key)
            if cached:
                logger.debug("Cache hit for query")
                return QueryResult(data=cached, rate_limit=self._rate_limit)
        
        # Wait for rate limit if needed
        await self._wait_for_rate_limit()
        
        # Ensure client is initialized
        if not self._client:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        
        # Execute with retries
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(
                    self.GITHUB_GRAPHQL_URL,
                    json={"query": query, "variables": variables},
                )
                
                self._update_rate_limit(response.headers)
                
                if response.status_code == 200:
                    result = response.json()
                    execution_time = time.time() - start_time
                    
                    # Cache successful results
                    if use_cache and "errors" not in result:
                        self._update_cache(cache_key, result.get("data", {}))
                    
                    return QueryResult(
                        data=result.get("data", {}),
                        errors=result.get("errors", []),
                        rate_limit=self._rate_limit,
                        execution_time=execution_time,
                    )
                
                elif response.status_code == 403:
                    # Rate limit exceeded
                    await self._wait_for_rate_limit()
                    continue
                    
                else:
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Query attempt {attempt + 1} failed: {e}")
            
            # Exponential backoff
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        return QueryResult(
            data={},
            errors=[{"message": f"Query failed after {self.max_retries} attempts: {last_error}"}],
            rate_limit=self._rate_limit,
            execution_time=time.time() - start_time,
        )
    
    async def paginate(
        self,
        query: str,
        variables: dict[str, Any],
        path: list[str],
        page_size: int = 100,
        max_pages: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a paginated GraphQL query.
        
        Args:
            query: GraphQL query with pagination variables ($first, $after).
            variables: Base query variables.
            path: Path to the paginated field in the response.
            page_size: Number of items per page.
            max_pages: Maximum number of pages to fetch.
            
        Returns:
            List of all items across all pages.
        """
        all_items = []
        cursor = None
        page = 0
        
        while True:
            page_vars = {**variables, "first": page_size, "after": cursor}
            result = await self.execute(query, page_vars, use_cache=False)
            
            if not result.success:
                logger.error(f"Pagination failed: {result.errors}")
                break
            
            # Navigate to the paginated field
            data = result.data
            for key in path:
                data = data.get(key, {})
            
            nodes = data.get("nodes", [])
            all_items.extend(nodes)
            
            # Check for next page
            page_info = data.get("pageInfo", {})
            if not page_info.get("hasNextPage", False):
                break
            
            cursor = page_info.get("endCursor")
            page += 1
            
            if max_pages and page >= max_pages:
                break
        
        return all_items
    
    @property
    def rate_limit(self) -> RateLimitInfo:
        """Get current rate limit information."""
        return self._rate_limit


# Predefined queries for common operations
class CommonQueries:
    """Collection of common GraphQL queries."""
    
    VIEWER = """
    query {
        viewer {
            login
            name
            email
            avatarUrl
        }
    }
    """
    
    ORGANIZATION = """
    query($login: String!) {
        organization(login: $login) {
            id
            name
            description
            url
            avatarUrl
            repositories(first: $first, after: $after) {
                totalCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    id
                    name
                    description
                    url
                    primaryLanguage { name }
                    defaultBranchRef { name }
                    createdAt
                    updatedAt
                    stargazerCount
                    forkCount
                }
            }
        }
    }
    """
    
    REPOSITORY = """
    query($owner: String!, $name: String!) {
        repository(owner: $owner, name: $name) {
            id
            name
            description
            url
            primaryLanguage { name }
            defaultBranchRef { name }
            createdAt
            updatedAt
            stargazerCount
            forkCount
            issues(first: 10, states: OPEN) {
                totalCount
                nodes {
                    number
                    title
                    state
                }
            }
            pullRequests(first: 10, states: OPEN) {
                totalCount
                nodes {
                    number
                    title
                    state
                }
            }
        }
    }
    """
    
    REPOSITORY_FILES = """
    query($owner: String!, $name: String!, $expression: String!) {
        repository(owner: $owner, name: $name) {
            object(expression: $expression) {
                ... on Tree {
                    entries {
                        name
                        type
                        path
                    }
                }
            }
        }
    }
    """
