"""用户资料相关 Inspect 场景。"""

from __future__ import annotations

from inspect_ai import Task, task

from evals._common import USER_TOOLS, agent_task, unique_user


@task
def user_profile_flow() -> Task:
    """注册登录 → 更新资料 → get_current_user 核对。"""
    username, email, password = unique_user("prof")
    prompt = f"""你只能通过提供的 MCP tools 完成任务，不要编造结果。

步骤：
1. register_user：username={username}, email={email}, password={password}, display_name=Before
2. login_user 获取 access_token
3. update_user_profile：display_name=AfterInspect, bio=Inspect profile ok
4. get_current_user：确认 display_name 为 AfterInspect，且 bio 包含 Inspect profile ok
5. 一句话总结；最终答案必须原样包含：PROFILE_OK

任一步失败则说明原因，且不要写 PROFILE_OK。
"""
    return agent_task(
        prompt=prompt,
        target="PROFILE_OK",
        tools=USER_TOOLS,
        metadata={"username": username, "scenario": "user_profile_flow"},
    )
