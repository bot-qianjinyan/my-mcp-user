#!/usr/bin/env python3
"""简单的 Streamable HTTP MCP 客户端，用于本地验证。"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp.client import Client

from app.config import settings


def _redact(text: str) -> str:
    return re.sub(r'"access_token"\s*:\s*"[^"]+"', '"access_token":"***"', text)


def _text(result) -> str:
    parts = []
    for item in getattr(result, "content", []) or []:
        if getattr(item, "type", None) == "text":
            parts.append(item.text)
    return _redact("\n".join(parts) or str(result))


async def main() -> None:
    url = f"http://{settings.mcp_host}:{settings.mcp_port}/mcp"
    async with Client(url) as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools.tools])

        resources = await client.list_resources()
        print("Resources:", [r.uri for r in resources.resources])

        prompts = await client.list_prompts()
        print("Prompts:", [p.name for p in prompts.prompts])

        reg = await client.call_tool(
            "register_user",
            {
                "username": "bob",
                "email": "bob@example.com",
                "password": "secret123",
                "display_name": "Bob",
            },
        )
        print("register:", _text(reg))

        login = await client.call_tool(
            "login_user",
            {"username": "bob", "password": "secret123"},
        )
        print("login:", _text(login))

        raw_login = "\n".join(
            item.text
            for item in (getattr(login, "content", []) or [])
            if getattr(item, "type", None) == "text"
        )
        payload = json.loads(raw_login)
        token = payload.get("access_token")
        if not token:
            print("login failed, skip authenticated calls")
            return

        me = await client.call_tool("get_current_user", {"access_token": token})
        print("me:", _text(me))

        updated = await client.call_tool(
            "update_user_profile",
            {"access_token": token, "bio": "from MCP client"},
        )
        print("update:", _text(updated))
        health = await client.read_resource("user://api/health")
        print("resource health:", health)

        prompt = await client.get_prompt("welcome_new_user", {"username": "bob"})
        print("prompt:", prompt)


if __name__ == "__main__":
    asyncio.run(main())
