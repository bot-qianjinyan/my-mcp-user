"""L1b — 表面指纹：与 golden JSON 对齐。"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from mcp.client import Client

from mcp_server.server import mcp

GOLDEN_PATH = Path(__file__).with_name("surface.golden.json")


def _load_golden() -> dict:
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_surface_matches_golden() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()
        templates = await client.list_resource_templates()

        live = {
            "tools": sorted(t.name for t in tools.tools),
            "resources": sorted(str(r.uri) for r in resources.resources),
            "resource_templates": sorted(
                getattr(t, "uriTemplate", None) or getattr(t, "uri_template")
                for t in (
                    getattr(templates, "resourceTemplates", None)
                    or getattr(templates, "resource_templates", [])
                )
            ),
            "prompts": sorted(p.name for p in prompts.prompts),
        }

        if os.getenv("UPDATE_GOLDEN") == "1":
            GOLDEN_PATH.write_text(
                json.dumps(live, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            pytest.skip("golden updated; re-run without UPDATE_GOLDEN=1")

        golden = _load_golden()
        assert live["tools"] == sorted(golden["tools"])
        assert live["resources"] == sorted(golden["resources"])
        assert live["resource_templates"] == sorted(golden["resource_templates"])
        assert live["prompts"] == sorted(golden["prompts"])
