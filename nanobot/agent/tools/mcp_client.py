"""MCP client for communicating with mcp-web-search server."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from loguru import logger


class MCPClient:
    """
    Async MCP client for web-search server communication.

    This client communicates with the mcp-web-search MCP server
    via stdio transport using the MCP protocol.
    """

    def __init__(self):
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        if not self._process or self._process.stdin is None:
            raise RuntimeError("MCP server process not running")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }

        request_json = json.dumps(request) + "\n"

        logger.debug(f"MCP Client sending: {request_json.strip()}")

        self._process.stdin.write(request_json.encode())
        await self._process.stdin.drain()

        # Read response
        if self._process.stdout is None:
            raise RuntimeError("MCP server stdout not available")

        response_line = await self._process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from MCP server")

        response = json.loads(response_line.decode())
        logger.debug(f"MCP Client received: {response}")

        if "error" in response:
            raise RuntimeError(f"MCP error: {response['error']}")

        return response.get("result", {})

    async def _initialize(self) -> None:
        """Initialize the MCP session."""
        await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "nanobot",
                "version": "0.1.3"
            }
        })

    async def start(self) -> None:
        """Start the MCP server process."""
        if self._process is not None:
            return  # Already started

        logger.info("Starting MCP web-search server...")

        # Find the project root (where mcp_web_search_wrapper.py is located)
        # Go up from nanobot/agent/tools/mcp_client.py to project root
        current_path = Path(__file__).resolve()
        project_root = current_path.parent.parent.parent.parent
        wrapper_path = project_root / "mcp_web_search_wrapper.py"

        logger.debug(f"Using MCP wrapper: {wrapper_path}")

        if not wrapper_path.exists():
            raise RuntimeError(f"MCP wrapper not found at {wrapper_path}")

        self._process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(wrapper_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Wait a bit for the server to start
        await asyncio.sleep(0.5)

        try:
            await self._initialize()
            logger.info("MCP web-search server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            await self.stop()
            raise

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        if self._process is None:
            await self.start()

        result = await self._send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        })

        # Extract content from MCP tool response
        if isinstance(result, dict):
            if "content" in result:
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    # Return the text content from the first content item
                    first_item = content[0]
                    if isinstance(first_item, dict) and "text" in first_item:
                        return first_item["text"]
                elif isinstance(content, str):
                    return content
            return result

        return str(result)

    async def stop(self) -> None:
        """Stop the MCP server process."""
        if self._process:
            try:
                self._process.terminate()
                await self._process.wait()
            except Exception as e:
                logger.error(f"Error stopping MCP server: {e}")
            finally:
                self._process = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
