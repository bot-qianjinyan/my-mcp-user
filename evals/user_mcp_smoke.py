"""最小 Inspect 评测：注册 → 登录 → 创建账单（冒烟）。

运行：
    ./scripts/run_inspect_gemini.sh google/gemini-3.6-flash evals/user_mcp_smoke.py
"""

from __future__ import annotations

from inspect_ai import Task, task

from evals._common import agent_task, unique_user


@task
def user_mcp_smoke() -> Task:
    """注册 → 登录 → 创建一笔账单，验证 Agent 能调用本仓库 MCP tools。"""
    username, email, password = unique_user("insp")
    prompt = f"""你只能通过提供的 MCP tools 完成任务，不要编造结果。

步骤：
1. 调用 register_user：username={username}, email={email}, password={password}, display_name=Inspect Smoke
2. 调用 login_user：username={username}, password={password}，记下返回的 access_token
3. 用该 access_token 调用 create_bill：title=Inspect午餐, amount=36.5, category=food
4. 完成后用一句话总结；务必在最终回答中原样包含标记：SMOKE_OK

若任一步失败，说明错误原因，且不要写 SMOKE_OK。
"""
    return agent_task(
        prompt=prompt,
        target="SMOKE_OK",
        tools=["register_user", "login_user", "create_bill"],
        metadata={"username": username, "scenario": "user_mcp_smoke"},
    )
