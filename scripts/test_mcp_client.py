#!/usr/bin/env python3
"""简单的 Streamable HTTP MCP 客户端，验证用户 + 账单能力。"""

from __future__ import annotations

import asyncio
import json
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.client import Client

from app.config import settings


def _redact(text: str) -> str:
    text = re.sub(r'"access_token"\s*:\s*"[^"]+"', '"access_token":"***"', text)
    return re.sub(r"bill://(?:mine|shared|item)/[^/\s'\"]+", "bill://***/***", text)


def _text(result) -> str:
    parts = []
    for item in getattr(result, "content", []) or []:
        if getattr(item, "type", None) == "text":
            parts.append(item.text)
    return _redact("\n".join(parts) or str(result))


def _raw_text(result) -> str:
    return "\n".join(
        item.text
        for item in (getattr(result, "content", []) or [])
        if getattr(item, "type", None) == "text"
    )


async def main() -> None:
    url = f"http://{settings.mcp_host}:{settings.mcp_port}/mcp"
    suffix = uuid.uuid4().hex[:6]
    owner = f"mcp_owner_{suffix}"
    friend = f"mcp_friend_{suffix}"

    async with Client(url) as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools.tools])
        resources = await client.list_resources()
        print("Resources:", [r.uri for r in resources.resources])
        prompts = await client.list_prompts()
        print("Prompts:", [p.name for p in prompts.prompts])

        await client.call_tool(
            "register_user",
            {
                "username": owner,
                "email": f"{owner}@example.com",
                "password": "secret123",
                "display_name": "Owner",
            },
        )
        await client.call_tool(
            "register_user",
            {
                "username": friend,
                "email": f"{friend}@example.com",
                "password": "secret123",
                "display_name": "Friend",
            },
        )

        login = await client.call_tool(
            "login_user",
            {"username": owner, "password": "secret123"},
        )
        print("login owner:", _text(login))
        owner_token = json.loads(_raw_text(login))["access_token"]

        friend_login = await client.call_tool(
            "login_user",
            {"username": friend, "password": "secret123"},
        )
        friend_token = json.loads(_raw_text(friend_login))["access_token"]

        created = await client.call_tool(
            "create_bill",
            {
                "access_token": owner_token,
                "title": "咖啡",
                "amount": 18.5,
                "category": "drink",
                "note": "morning",
                "spent_at": "2026-08-11",
            },
        )
        print("create_bill:", _text(created))
        bill_id = json.loads(_raw_text(created))["id"]

        print("list_my_bills:", _text(await client.call_tool("list_my_bills", {"access_token": owner_token})))
        print(
            "update_bill:",
            _text(
                await client.call_tool(
                    "update_bill",
                    {"access_token": owner_token, "bill_id": bill_id, "amount": 20},
                )
            ),
        )
        print(
            "share_bill:",
            _text(
                await client.call_tool(
                    "share_bill",
                    {"access_token": owner_token, "bill_id": bill_id, "username": friend},
                )
            ),
        )
        print(
            "list_shared_bills:",
            _text(await client.call_tool("list_shared_bills", {"access_token": friend_token})),
        )
        print(
            "like_bill friend:",
            _text(await client.call_tool("like_bill", {"access_token": friend_token, "bill_id": bill_id})),
        )
        print(
            "like_bill owner:",
            _text(await client.call_tool("like_bill", {"access_token": owner_token, "bill_id": bill_id})),
        )
        print(
            "get_bill:",
            _text(await client.call_tool("get_bill", {"access_token": owner_token, "bill_id": bill_id})),
        )

        health = await client.read_resource("user://api/health")
        print("resource health:", health)
        mine = await client.read_resource(f"bill://mine/{owner_token}")
        print("resource my bills:", _redact(str(mine)))
        prompt = await client.get_prompt("help_create_bill", {"category": "food"})
        print("prompt:", prompt)


if __name__ == "__main__":
    asyncio.run(main())
