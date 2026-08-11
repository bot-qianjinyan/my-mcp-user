"""L1c — Resource / Prompt 冒烟。"""

from __future__ import annotations

import pytest
from mcp.client import Client

from mcp_server.server import mcp


def _resource_text(result) -> str:
    parts: list[str] = []
    for item in getattr(result, "contents", []) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts)


@pytest.mark.asyncio
async def test_read_static_docs_overview() -> None:
    async with Client(mcp) as client:
        result = await client.read_resource("user://docs/overview")
        body = _resource_text(result)
        assert body
        assert "Bills" in body or "账单" in body or "/api/bills" in body


@pytest.mark.asyncio
async def test_read_api_health_resource() -> None:
    """即使上游 API 未启动，resource 调用本身也应返回内容（ok true/false）。"""
    async with Client(mcp) as client:
        result = await client.read_resource("user://api/health")
        body = _resource_text(result)
        assert body
        assert '"ok"' in body


@pytest.mark.asyncio
async def test_get_welcome_prompt() -> None:
    async with Client(mcp) as client:
        result = await client.get_prompt("welcome_new_user", {"username": "alice"})
        assert result.messages
        text = result.messages[0].content.text
        assert "alice" in text


@pytest.mark.asyncio
async def test_get_help_create_bill_prompt() -> None:
    async with Client(mcp) as client:
        result = await client.get_prompt("help_create_bill", {"category": "food"})
        assert result.messages
        text = result.messages[0].content.text
        assert "food" in text
        assert "create_bill" in text
