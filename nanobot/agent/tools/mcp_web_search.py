"""MCP Web Search tool using mcp-web-search server."""

from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool
from nanobot.agent.tools.mcp_client import MCPClient


class WebSearchPrimeTool(Tool):
    """
    Search the web using MCP web-search server.

    This tool communicates with the mcp-web-search MCP server
    to perform web searches using SEARXNG.
    """

    name = "web_search_prime"
    description = (
        "Search the web and return comprehensive results with titles, URLs, and content summaries. "
        "Use this tool when you need to find current information from the internet."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (1-10)",
                "minimum": 1,
                "maximum": 10,
                "default": 5
            }
        },
        "required": ["query"]
    }

    def __init__(self, timeout: float = 30.0):
        """
        Initialize the MCP web search tool.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self._client: MCPClient | None = None

    async def _get_client(self) -> MCPClient:
        """Get or create the MCP client."""
        if self._client is None:
            self._client = MCPClient()
            await self._client.start()
        return self._client

    async def execute(self, query: str, max_results: int = 5, **kwargs: Any) -> str:
        """
        Execute web search using the MCP server.

        Args:
            query: Search query
            max_results: Maximum number of results
            **kwargs: Additional arguments (ignored)

        Returns:
            Formatted search results as a string
        """
        try:
            client = await self._get_client()

            logger.info(f"Executing MCP web search for query: {query}")

            result = await client.call_tool(
                "search_web_tool",
                {"query": query}
            )

            if not result or not isinstance(result, str):
                return f"No results found for query: {query}"

            # The mcp-web-search server returns formatted content
            # We just need to ensure it's properly returned
            return result

        except Exception as e:
            logger.error(f"MCP web search error: {e}")
            return f"Error performing web search: {str(e)}"

    async def cleanup(self) -> None:
        """Clean up resources."""
        if self._client:
            try:
                await self._client.stop()
            except Exception as e:
                logger.error(f"Error cleaning up MCP client: {e}")
            finally:
                self._client = None
