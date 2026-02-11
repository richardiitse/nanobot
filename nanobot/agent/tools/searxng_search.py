"""SearXNG web search tool - direct API implementation."""

import os
from typing import Any

import httpx

from nanobot.agent.tools.base import Tool


class SearXNGSearchTool(Tool):
    """
    Search the web using SearXNG API directly.

    This is a fallback implementation that doesn't require MCP server.
    It provides simpler web search functionality with fewer dependencies.

    Environment Variables:
        SEARXNG_API_BASE: Base URL of SearXNG instance (default: public instances)
    """

    name = "web_search"
    description = (
        "Search the web and return comprehensive results with titles, URLs, and snippets. "
        "Use this tool when you need to find current information from the internet."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string"
            },
            "count": {
                "type": "integer",
                "description": "Number of results to return (1-10)",
                "minimum": 1,
                "maximum": 10,
                "default": 5
            }
        },
        "required": ["query"]
    }

    # Default public SearXNG instances (fallback)
    DEFAULT_INSTANCES = [
        "https://search.brave.com",  # Brave Search (has SearXNG-compatible API)
    ]

    def __init__(self, api_base: str | None = None, max_results: int = 5):
        """
        Initialize the SearXNG search tool.

        Args:
            api_base: Base URL of SearXNG instance (from SEARXNG_API_BASE env var if None)
            max_results: Default maximum number of results
        """
        self.api_base = api_base or os.environ.get("SEARXNG_API_BASE")
        self.max_results = max_results

    async def execute(self, query: str, count: int | None = None, **kwargs: Any) -> str:
        """
        Execute web search using SearXNG API.

        Args:
            query: Search query
            count: Number of results to return (uses max_results if None)
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted search results as a string
        """
        if not self.api_base:
            return "Error: SEARXNG_API_BASE not configured. Set this environment variable or pass api_base parameter."

        n = min(max(count or self.max_results, 1), 10)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.api_base}/search",
                    params={
                        "q": query,
                        "format": "json",
                    },
                    headers={"User-Agent": "Mozilla/5.0 (compatible; nanobot/1.0)"}
                )
                response.raise_for_status()

            data = response.json()

            # Handle different SearXNG response formats
            results = []
            if "results" in data:
                results = data["results"]
            elif isinstance(data, list):
                results = data

            if not results:
                return f"No results found for query: {query}"

            # Format results
            lines = [f"Results for: {query}\n"]
            for i, result in enumerate(results[:n], 1):
                title = result.get("title", "No title")
                url = result.get("url", result.get("link", ""))
                snippet = result.get("content", result.get("snippet", result.get("description", "")))

                lines.append(f"{i}. {title}")
                lines.append(f"   {url}")
                if snippet:
                    # Clean up snippet
                    snippet = snippet.strip()
                    snippet = snippet[:200] + "..." if len(snippet) > 200 else snippet
                    lines.append(f"   {snippet}")
                lines.append("")

            return "\n".join(lines)

        except httpx.HTTPError as e:
            return f"Error performing web search: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
