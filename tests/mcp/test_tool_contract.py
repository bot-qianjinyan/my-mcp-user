"""L1 — 工具契约：名称、描述、inputSchema。"""

from __future__ import annotations

import pytest
from mcp.client import Client

from mcp_server.server import mcp


@pytest.mark.asyncio
async def test_tool_contract() -> None:
    async with Client(mcp) as client:
        result = await client.list_tools()
        tools = result.tools
        assert tools, "tools/list should not be empty"

        names = [t.name for t in tools]
        assert len(names) == len(set(names)), "tool names must be unique"

        for tool in tools:
            assert tool.name, "tool name required"
            assert len(tool.name) <= 64, f"tool name too long: {tool.name}"
            assert tool.description and tool.description.strip(), f"missing description: {tool.name}"

            schema = tool.inputSchema if hasattr(tool, "inputSchema") else None
            if schema is None:
                dump = tool.model_dump()
                schema = dump.get("inputSchema") or dump.get("input_schema")

            assert isinstance(schema, dict), f"inputSchema missing for {tool.name}"
            assert schema.get("type") == "object", f"inputSchema.type must be object: {tool.name}"
            assert "properties" in schema, f"inputSchema.properties missing: {tool.name}"
