#!/usr/bin/env python3
"""独立测试 MCP 用户相关 Tools / Resources / Prompts。"""

from __future__ import annotations

import asyncio
import uuid

from mcp.client import Client

from mcp_helpers import mcp_url, parse_json, print_catalog, redact, text


async def main() -> None:
    url = mcp_url()
    suffix = uuid.uuid4().hex[:6]
    username = f"mcp_user_{suffix}"
    print(f"MCP url: {url}")
    print("=== MCP User tests ===")

    async with Client(url) as client:
        await print_catalog(client)

        reg = await client.call_tool(
            "register_user",
            {
                "username": username,
                "email": f"{username}@example.com",
                "password": "secret123",
                "display_name": "MCP User",
            },
        )
        print("register_user:", text(reg))

        login = await client.call_tool(
            "login_user",
            {"username": username, "password": "secret123"},
        )
        print("login_user:", text(login))
        token = parse_json(login)["access_token"]

        me = await client.call_tool("get_current_user", {"access_token": token})
        print("get_current_user:", text(me))

        updated = await client.call_tool(
            "update_user_profile",
            {"access_token": token, "display_name": "MCP User Updated", "bio": "from mcp user test"},
        )
        print("update_user_profile:", text(updated))

        health = await client.read_resource("user://api/health")
        print("resource health:", health)

        profile = await client.read_resource(f"user://profile/{token}")
        print("resource profile:", redact(str(profile)))

        prompt = await client.get_prompt("welcome_new_user", {"username": username})
        print("prompt welcome_new_user:", prompt)

        help_prompt = await client.get_prompt("help_update_profile", {"field": "bio"})
        print("prompt help_update_profile:", help_prompt)

    print(f"All MCP user checks passed. user={username}")


if __name__ == "__main__":
    asyncio.run(main())
