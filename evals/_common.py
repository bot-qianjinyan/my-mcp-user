"""Inspect 评测公共工具：对接本仓库 Streamable HTTP MCP。"""

from __future__ import annotations

import os
import uuid

from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.scorer import includes
from inspect_ai.tool import mcp_server_http, mcp_tools


def mcp_url() -> str:
    return os.environ.get("USER_MCP_URL", "http://127.0.0.1:3001/mcp")


def mcp_server():
    return mcp_server_http(name="user-mcp", url=mcp_url())


def unique_user(prefix: str = "insp") -> tuple[str, str, str]:
    """返回 (username, email, password)。"""
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    return username, f"{username}@example.com", "Passw0rd!"


def agent_task(
    *,
    prompt: str,
    target: str,
    tools: list[str],
    metadata: dict | None = None,
    attempts: int = 3,
) -> Task:
    server = mcp_server()
    return Task(
        dataset=[
            Sample(
                input=prompt,
                target=target,
                metadata=metadata or {},
            )
        ],
        solver=react(
            prompt=(
                "你是评测 Agent。严格使用提供的 MCP tools 完成用户指令，"
                "不要跳过工具调用，不要伪造 token / 账单 / 用户数据。"
                "工具返回 JSON 后，再进行下一步；最终必须调用 submit 提交答案。"
            ),
            tools=[mcp_tools(server, tools=tools)],
            attempts=attempts,
        ),
        scorer=includes(),
    )


USER_TOOLS = [
    "register_user",
    "login_user",
    "get_current_user",
    "update_user_profile",
]

BILL_TOOLS = [
    "create_bill",
    "list_my_bills",
    "list_shared_bills",
    "get_bill",
    "update_bill",
    "delete_bill",
    "share_bill",
    "unshare_bill",
    "like_bill",
    "unlike_bill",
]

ALL_AUTH_BILL_TOOLS = USER_TOOLS + BILL_TOOLS
