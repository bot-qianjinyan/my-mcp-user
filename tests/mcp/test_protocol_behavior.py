"""L4-lite — 协议行为：list 可用、未知工具/缺参被拒。"""

from __future__ import annotations

import pytest
from mcp.client import Client

from mcp_server.server import mcp


@pytest.mark.asyncio
async def test_list_tools_not_empty() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        assert tools.tools
        names = {t.name for t in tools.tools}
        assert "login_user" in names
        assert "create_bill" in names


@pytest.mark.asyncio
async def test_unknown_tool_is_error() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("no_such_tool", {})
        assert result.is_error is True


@pytest.mark.asyncio
async def test_missing_required_args_is_error() -> None:
    async with Client(mcp) as client:
        result = await client.call_tool("create_bill", {})
        assert result.is_error is True
        text = "".join(
            item.text
            for item in (result.content or [])
            if getattr(item, "type", None) == "text"
        )
        assert "access_token" in text or "Field required" in text or "validation" in text.lower()
