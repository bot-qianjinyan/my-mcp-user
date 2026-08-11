#!/usr/bin/env python3
"""独立测试 MCP 账单相关 Tools / Resources / Prompts。"""

from __future__ import annotations

import asyncio
import uuid

from mcp.client import Client

from mcp_helpers import mcp_url, parse_json, print_catalog, redact, text


async def main() -> None:
    url = mcp_url()
    suffix = uuid.uuid4().hex[:6]
    owner = f"mcp_owner_{suffix}"
    friend = f"mcp_friend_{suffix}"
    print(f"MCP url: {url}")
    print("=== MCP Bill tests ===")

    async with Client(url) as client:
        await print_catalog(client)

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

        owner_login = await client.call_tool(
            "login_user",
            {"username": owner, "password": "secret123"},
        )
        friend_login = await client.call_tool(
            "login_user",
            {"username": friend, "password": "secret123"},
        )
        owner_token = parse_json(owner_login)["access_token"]
        friend_token = parse_json(friend_login)["access_token"]
        print("login owner/friend: ok")

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
        print("create_bill:", text(created))
        bill_id = parse_json(created)["id"]

        print(
            "list_my_bills:",
            text(await client.call_tool("list_my_bills", {"access_token": owner_token})),
        )
        print(
            "update_bill:",
            text(
                await client.call_tool(
                    "update_bill",
                    {"access_token": owner_token, "bill_id": bill_id, "amount": 20},
                )
            ),
        )
        print(
            "share_bill:",
            text(
                await client.call_tool(
                    "share_bill",
                    {"access_token": owner_token, "bill_id": bill_id, "username": friend},
                )
            ),
        )
        print(
            "list_shared_bills:",
            text(await client.call_tool("list_shared_bills", {"access_token": friend_token})),
        )
        print(
            "like_bill friend:",
            text(await client.call_tool("like_bill", {"access_token": friend_token, "bill_id": bill_id})),
        )
        print(
            "like_bill owner:",
            text(await client.call_tool("like_bill", {"access_token": owner_token, "bill_id": bill_id})),
        )
        print(
            "get_bill:",
            text(await client.call_tool("get_bill", {"access_token": owner_token, "bill_id": bill_id})),
        )
        print(
            "unlike_bill:",
            text(await client.call_tool("unlike_bill", {"access_token": friend_token, "bill_id": bill_id})),
        )
        print(
            "unshare_bill:",
            text(
                await client.call_tool(
                    "unshare_bill",
                    {"access_token": owner_token, "bill_id": bill_id, "username": friend},
                )
            ),
        )
        print(
            "delete_bill:",
            text(await client.call_tool("delete_bill", {"access_token": owner_token, "bill_id": bill_id})),
        )

        mine = await client.read_resource(f"bill://mine/{owner_token}")
        print("resource my bills:", redact(str(mine)))
        shared = await client.read_resource(f"bill://shared/{friend_token}")
        print("resource shared bills:", redact(str(shared)))

        prompt = await client.get_prompt("help_create_bill", {"category": "food"})
        print("prompt help_create_bill:", prompt)
        share_prompt = await client.get_prompt(
            "help_share_bill",
            {"bill_id": str(bill_id), "target_username": friend},
        )
        print("prompt help_share_bill:", share_prompt)
        like_prompt = await client.get_prompt("help_like_bill", {"bill_id": str(bill_id)})
        print("prompt help_like_bill:", like_prompt)

    print(f"All MCP bill checks passed. owner={owner}, friend={friend}")


if __name__ == "__main__":
    asyncio.run(main())
