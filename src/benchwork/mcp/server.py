"""STDIO-only Model Context Protocol server for Benchwork."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from .. import __version__
from .instructions import SERVER_INSTRUCTIONS
from .runtime import BenchworkTools
from .tools_canon import register_canon_tools
from .tools_experiment import register_experiment_tools
from .tools_read import register_read_tools
from .tools_task import register_task_tools


class BenchworkMCPServer(MCPServer):
    """MCPServer with a Python 3.13-safe explicit STDIO stream binding."""

    async def run_stdio_async(self) -> None:
        # MCP SDK 2.0's AsyncFile reader can stall for piped Python 3.13
        # subprocesses. Keep SDK tool metadata and dispatch, but bind the
        # newline-framed STDIO transport with asyncio's native pipe reader.
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_running_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        while line := await reader.readline():
            try:
                request = json.loads(line)
                response = await self._dispatch_stdio(request)
            except (ValueError, TypeError, json.JSONDecodeError) as error:
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": str(error)},
                }
            if response is not None:
                sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
                sys.stdout.flush()

    async def _dispatch_stdio(self, request: dict[str, Any]) -> dict[str, Any] | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            raise ValueError("invalid JSON-RPC request")
        method = request.get("method")
        request_id = request.get("id")
        if request_id is None:
            return None
        if method == "initialize":
            options = self._lowlevel_server.create_initialization_options()
            requested = request.get("params", {}).get("protocolVersion", "2025-11-25")
            init_result = {
                "protocolVersion": requested,
                "capabilities": options.capabilities.model_dump(
                    by_alias=True,
                    exclude_none=True,
                ),
                "serverInfo": {
                    "name": options.server_name,
                    "version": options.server_version,
                },
                "instructions": options.instructions,
            }
            if options.title is not None:
                init_result["serverInfo"]["title"] = options.title
            return {"jsonrpc": "2.0", "id": request_id, "result": init_result}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            tools = await self.list_tools()
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [
                        tool.model_dump(by_alias=True, exclude_none=True)
                        for tool in tools
                    ]
                },
            }
        if method == "tools/call":
            parameters = request.get("params")
            if not isinstance(parameters, dict) or not isinstance(
                parameters.get("name"), str
            ):
                raise ValueError("tools/call requires a tool name")
            tool_result = await self.call_tool(
                parameters["name"],
                parameters.get("arguments") or {},
            )
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": tool_result.model_dump(by_alias=True, exclude_none=True),
            }
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"method not found: {method}"},
        }


def create_server(root: Path | None = None) -> MCPServer:
    server = BenchworkMCPServer(
        "benchwork",
        title="Benchwork scientific control plane",
        description="Typed access to canonical Benchwork research state.",
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
    )
    tools = BenchworkTools(root)
    register_read_tools(server, tools)
    register_task_tools(server, tools)
    register_canon_tools(server, tools)
    register_experiment_tools(server, tools)
    return server


mcp = create_server()


def run() -> None:
    """Run the server over STDIO, the only Phase 2 transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
