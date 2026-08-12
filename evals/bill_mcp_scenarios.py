"""账单相关 Inspect 场景：CRUD / 点赞 / 分享协同。

前置：API :8000 + MCP :3001 已启动；配置模型 API Key。

运行单个文件（会跑本文件全部 @task）：
    ./scripts/run_inspect_gemini.sh google/gemini-3.6-flash evals/bill_mcp_scenarios.py

只跑某一个 task：
    inspect eval evals/bill_mcp_scenarios.py@bill_crud_flow --model google/gemini-3.6-flash

说明见 docs/INSPECT_MCP.zh.md。
"""

from __future__ import annotations

from inspect_ai import Task, task

from evals._common import ALL_AUTH_BILL_TOOLS, agent_task, unique_user


@task
def bill_crud_flow() -> Task:
    """注册登录 → 创建/列表/详情/更新/删除账单。"""
    username, email, password = unique_user("bill")
    prompt = f"""你只能通过提供的 MCP tools 完成任务，不要编造结果。

步骤：
1. register_user：username={username}, email={email}, password={password}, display_name=Bill CRUD
2. login_user：username={username}, password={password}，记下 access_token
3. create_bill：title=咖啡, amount=28.0, category=food, note=Inspect CRUD
4. list_my_bills：确认能看到刚创建的账单，记下 bill_id
5. get_bill：读取该 bill_id
6. update_bill：把 amount 改为 30.5，note 改为 已改价
7. 再 get_bill：确认 amount 已更新
8. delete_bill：删除该账单
9. list_my_bills：确认该账单已不在列表中
10. 一句话总结；最终答案必须原样包含：CRUD_OK

任一步失败则说明原因，且不要写 CRUD_OK。
"""
    return agent_task(
        prompt=prompt,
        target="CRUD_OK",
        tools=ALL_AUTH_BILL_TOOLS,
        metadata={"username": username, "scenario": "bill_crud_flow"},
        attempts=4,
    )


@task
def bill_like_flow() -> Task:
    """创建账单后点赞，并核对 like_count。"""
    username, email, password = unique_user("like")
    prompt = f"""你只能通过提供的 MCP tools 完成任务，不要编造结果。

步骤：
1. register_user：username={username}, email={email}, password={password}, display_name=Bill Like
2. login_user 获取 access_token
3. create_bill：title=电影票, amount=80, category=entertainment
4. like_bill：点赞刚创建的账单
5. get_bill：确认 like_count >= 1 且 liked_by_me 为 true
6. unlike_bill：取消点赞
7. get_bill：确认 like_count 回到 0 或 liked_by_me 为 false
8. 一句话总结；最终答案必须原样包含：LIKE_OK

任一步失败则说明原因，且不要写 LIKE_OK。
"""
    return agent_task(
        prompt=prompt,
        target="LIKE_OK",
        tools=ALL_AUTH_BILL_TOOLS,
        metadata={"username": username, "scenario": "bill_like_flow"},
        attempts=4,
    )


@task
def bill_share_flow() -> Task:
    """双用户：A 创建并分享给 B，B 查看分享列表并点赞。"""
    owner, owner_email, password = unique_user("owner")
    peer, peer_email, _ = unique_user("peer")
    prompt = f"""你只能通过提供的 MCP tools 完成任务，不要编造结果。需要两个用户协作。

步骤：
1. 注册并登录账单主人 A：
   - register_user：username={owner}, email={owner_email}, password={password}, display_name=Owner
   - login_user：记下 owner_token
2. 注册并登录协作人 B：
   - register_user：username={peer}, email={peer_email}, password={password}, display_name=Peer
   - login_user：记下 peer_token
3. 用 owner_token 创建账单：title=团建晚餐, amount=320, category=food
4. 用 owner_token 调用 share_bill，把该账单分享给 username={peer}
5. 用 peer_token 调用 list_shared_bills，确认能看到该账单
6. 用 peer_token 调用 like_bill 点赞该账单
7. 用 owner_token 调用 get_bill，确认 like_count >= 1
8. 用 owner_token 调用 unshare_bill，取消对 {peer} 的分享
9. 用 peer_token 再 list_shared_bills，确认该账单不再出现（或不可见）
10. 一句话总结；最终答案必须原样包含：SHARE_OK

任一步失败则说明原因，且不要写 SHARE_OK。
注意：切换用户时必须使用对应用户的 access_token，不要混用。
"""
    return agent_task(
        prompt=prompt,
        target="SHARE_OK",
        tools=ALL_AUTH_BILL_TOOLS,
        metadata={
            "owner": owner,
            "peer": peer,
            "scenario": "bill_share_flow",
        },
        attempts=5,
    )


@task
def bill_list_filter_smoke() -> Task:
    """创建多笔账单后 list/get，验证能区分不同 category。"""
    username, email, password = unique_user("list")
    prompt = f"""你只能通过提供的 MCP tools 完成任务，不要编造结果。

步骤：
1. register_user / login_user：username={username}, email={email}, password={password}
2. 连续创建 3 笔账单：
   - title=地铁, amount=5, category=transport
   - title=午餐, amount=32, category=food
   - title=书, amount=68, category=education
3. list_my_bills：确认至少有 3 条
4. 任选其中一笔 get_bill，在最终总结中写明其 title 与 category
5. 一句话总结；最终答案必须原样包含：LIST_OK

任一步失败则说明原因，且不要写 LIST_OK。
"""
    return agent_task(
        prompt=prompt,
        target="LIST_OK",
        tools=ALL_AUTH_BILL_TOOLS,
        metadata={"username": username, "scenario": "bill_list_filter_smoke"},
        attempts=3,
    )
