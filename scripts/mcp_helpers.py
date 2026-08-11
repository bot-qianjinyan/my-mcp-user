"""共享的 MCP 测试小工具。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings


def mcp_url() -> str:
    return f"http://{settings.mcp_host}:{settings.mcp_port}/mcp"


def redact(text: str) -> str:
    text = re.sub(r'"access_token"\s*:\s*"[^"]+"', '"access_token":"***"', text)
    text = re.sub(r"user://profile/[^/\s'\"]+", "user://profile/***", text)
    return re.sub(r"bill://(?:mine|shared|item)/[^/\s'\"]+", "bill://***/***", text)


def text(result) -> str:
    parts = []
    for item in getattr(result, "content", []) or []:
        if getattr(item, "type", None) == "text":
            parts.append(item.text)
    return redact("\n".join(parts) or str(result))


def raw_text(result) -> str:
    return "\n".join(
        item.text
        for item in (getattr(result, "content", []) or [])
        if getattr(item, "type", None) == "text"
    )


def parse_json(result) -> dict:
    return json.loads(raw_text(result))


async def print_catalog(client) -> None:
    tools = await client.list_tools()
    print("Tools:", [t.name for t in tools.tools])
    resources = await client.list_resources()
    print("Resources:", [r.uri for r in resources.resources])
    prompts = await client.list_prompts()
    print("Prompts:", [p.name for p in prompts.prompts])
