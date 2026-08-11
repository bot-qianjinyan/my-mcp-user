"""最小 Inspect 评测：经 HTTP 对接本仓库 MCP（http://127.0.0.1:3001/mcp）。

前置：
1. 启动 REST API：uvicorn app.main:app --host 127.0.0.1 --port 8000
2. 启动 MCP：python -m mcp_server
3. pip install -r requirements-inspect.txt，并配置模型 API Key

运行：
    inspect eval evals/user_mcp_smoke.py --model openai/gpt-4o
    inspect view

说明见 docs/INSPECT_MCP.zh.md。
"""

from __future__ import annotations

import os
import uuid

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.scorer import includes
from inspect_ai.tool import mcp_server_http, mcp_tools


def _mcp_url() -> str:
    return os.environ.get("USER_MCP_URL", "http://127.0.0.1:3001/mcp")


@task
def user_mcp_smoke() -> Task:
    """注册 → 登录 → 创建一笔账单，验证 Agent 能调用本仓库 MCP tools。"""
    suffix = uuid.uuid4().hex[:8]
    username = f"insp_{suffix}"
    password = "Passw0rd!"
    email = f"{username}@example.com"

    user_mcp = mcp_server_http(
        name="user-mcp",
        url=_mcp_url(),
    )

    prompt = f"""你只能通过提供的 MCP tools 完成任务，不要编造结果。

步骤：
1. 调用 register_user：username={username}, email={email}, password={password}, display_name=Inspect Smoke
2. 调用 login_user：username={username}, password={password}，记下返回的 access_token
3. 用该 access_token 调用 create_bill：title=Inspect午餐, amount=36.5, category=food
4. 完成后用一句话总结；务必在最终回答中原样包含标记：SMOKE_OK

若任一步失败，说明错误原因，且不要写 SMOKE_OK。
"""

    return Task(
        dataset=[
            Sample(
                input=prompt,
                target="SMOKE_OK",
                metadata={"username": username},
            )
        ],
        solver=react(
            prompt=(
                "你是评测 Agent。严格使用工具完成用户指令，"
                "不要跳过工具调用，不要伪造 token 或账单结果。"
            ),
            tools=[
                mcp_tools(
                    user_mcp,
                    tools=["register_user", "login_user", "create_bill"],
                )
            ],
            attempts=3,
        ),
        scorer=includes(),
    )
