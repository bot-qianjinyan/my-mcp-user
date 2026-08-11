"""L2 — Mock HTTP：验证 MCP tools 是否正确调用 FastAPI。"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from mcp.client import Client

import mcp_server.server as server
from mcp_server.server import mcp


def _text(result) -> str:
    return "\n".join(
        item.text
        for item in (getattr(result, "content", []) or [])
        if getattr(item, "type", None) == "text"
    )


@pytest.fixture()
def api_mock(monkeypatch):
    """拦截 mcp_server.server 内的 httpx.Client，记录请求并返回假响应。"""
    captured: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body: Any = None
        if request.content:
            try:
                body = json.loads(request.content.decode())
            except json.JSONDecodeError:
                body = request.content.decode()

        captured.append(
            {
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "headers": {k.lower(): v for k, v in request.headers.items()},
                "json": body,
            }
        )

        path = request.url.path
        method = request.method.upper()

        if method == "POST" and path == "/api/users/login":
            return httpx.Response(
                200,
                json={
                    "access_token": "mock-token",
                    "token_type": "bearer",
                    "user": {
                        "id": 1,
                        "username": body.get("username") if isinstance(body, dict) else "u",
                        "email": "u@example.com",
                        "display_name": "U",
                        "bio": None,
                        "created_at": "2026-08-11T00:00:00",
                        "updated_at": "2026-08-11T00:00:00",
                    },
                },
            )

        if method == "GET" and path == "/api/users/me":
            return httpx.Response(
                200,
                json={
                    "id": 1,
                    "username": "alice",
                    "email": "alice@example.com",
                    "display_name": "Alice",
                    "bio": None,
                    "created_at": "2026-08-11T00:00:00",
                    "updated_at": "2026-08-11T00:00:00",
                },
            )

        if method == "POST" and path == "/api/bills":
            payload = body if isinstance(body, dict) else {}
            return httpx.Response(
                201,
                json={
                    "id": 42,
                    "owner_id": 1,
                    "owner_username": "alice",
                    "title": payload.get("title"),
                    "amount": str(payload.get("amount")),
                    "category": payload.get("category"),
                    "note": payload.get("note"),
                    "spent_at": payload.get("spent_at"),
                    "like_count": 0,
                    "liked_by_me": False,
                    "shared_with": [],
                    "created_at": "2026-08-11T00:00:00",
                    "updated_at": "2026-08-11T00:00:00",
                },
            )

        if method == "POST" and path.startswith("/api/bills/") and path.endswith("/share"):
            return httpx.Response(
                200,
                json={
                    "id": 42,
                    "owner_id": 1,
                    "owner_username": "alice",
                    "title": "咖啡",
                    "amount": "18.50",
                    "category": "drink",
                    "note": None,
                    "spent_at": None,
                    "like_count": 0,
                    "liked_by_me": False,
                    "shared_with": [body.get("username") if isinstance(body, dict) else "bob"],
                    "created_at": "2026-08-11T00:00:00",
                    "updated_at": "2026-08-11T00:00:00",
                },
            )

        if method == "GET" and path == "/api/bills":
            return httpx.Response(200, json=[])

        return httpx.Response(404, json={"detail": f"unmocked {method} {path}"})

    transport = httpx.MockTransport(handler)
    real_client_cls = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client_cls(*args, **kwargs)

    monkeypatch.setattr(server.httpx, "Client", client_factory)
    return captured


@pytest.mark.asyncio
async def test_login_user_posts_to_login_api(api_mock) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "login_user",
            {"username": "alice", "password": "secret123"},
        )

    assert result.is_error is False
    payload = json.loads(_text(result))
    assert payload["ok"] is True
    assert payload["access_token"] == "mock-token"

    assert len(api_mock) == 1
    req = api_mock[0]
    assert req["method"] == "POST"
    assert req["path"] == "/api/users/login"
    assert req["url"].startswith(server.settings.api_base_url.rstrip("/"))
    assert req["json"] == {"username": "alice", "password": "secret123"}
    assert "authorization" not in req["headers"]


@pytest.mark.asyncio
async def test_create_bill_posts_to_bills_api_with_bearer(api_mock) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_bill",
            {
                "access_token": "fake-token",
                "title": "咖啡",
                "amount": 18.5,
                "category": "drink",
                "note": "morning",
                "spent_at": "2026-08-11",
            },
        )

    assert result.is_error is False
    payload = json.loads(_text(result))
    assert payload["ok"] is True
    assert payload["id"] == 42
    assert payload["title"] == "咖啡"

    assert len(api_mock) == 1
    req = api_mock[0]
    assert req["method"] == "POST"
    assert req["path"] == "/api/bills"
    assert req["headers"].get("authorization") == "Bearer fake-token"
    assert req["json"]["title"] == "咖啡"
    assert float(req["json"]["amount"]) == 18.5
    assert req["json"]["category"] == "drink"
    assert req["json"]["note"] == "morning"
    assert req["json"]["spent_at"] == "2026-08-11"


@pytest.mark.asyncio
async def test_share_bill_posts_share_endpoint(api_mock) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "share_bill",
            {"access_token": "fake-token", "bill_id": 42, "username": "bob"},
        )

    assert result.is_error is False
    payload = json.loads(_text(result))
    assert payload["ok"] is True
    assert "bob" in payload["shared_with"]

    assert len(api_mock) == 1
    req = api_mock[0]
    assert req["method"] == "POST"
    assert req["path"] == "/api/bills/42/share"
    assert req["headers"].get("authorization") == "Bearer fake-token"
    assert req["json"] == {"username": "bob"}


@pytest.mark.asyncio
async def test_get_current_user_gets_me_with_bearer(api_mock) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "get_current_user",
            {"access_token": "fake-token"},
        )

    assert result.is_error is False
    payload = json.loads(_text(result))
    assert payload["ok"] is True
    assert payload["username"] == "alice"

    req = api_mock[0]
    assert req["method"] == "GET"
    assert req["path"] == "/api/users/me"
    assert req["headers"].get("authorization") == "Bearer fake-token"
    assert req["json"] is None


@pytest.mark.asyncio
async def test_list_my_bills_gets_bills_with_bearer(api_mock) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "list_my_bills",
            {"access_token": "fake-token"},
        )

    assert result.is_error is False
    payload = json.loads(_text(result))
    assert payload["ok"] is True
    assert payload["items"] == []

    req = api_mock[0]
    assert req["method"] == "GET"
    assert req["path"] == "/api/bills"
    assert req["headers"].get("authorization") == "Bearer fake-token"
