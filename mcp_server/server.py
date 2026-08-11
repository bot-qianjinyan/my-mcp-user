"""
User + Bill MCP Server — Streamable HTTP

MCP 三要素：
- Tools: 用户鉴权 + 账单 CRUD / 分享 / 点赞
- Resources: API 健康、文档、我的账单列表、单条账单
- Prompts: 欢迎、改资料、记账助手、分享助手
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings
from mcp.server import MCPServer

mcp = MCPServer(
    "user-mcp",
    instructions=(
        "用户与账单 MCP Server。"
        "鉴权：先 login_user 获取 access_token，再传给需要登录的工具。"
        "账单：可创建/读取/更新自己的账单，分享给他人阅读，点赞自己或他人分享给你的账单。"
    ),
)


def _api(path: str) -> str:
    return f"{settings.api_base_url.rstrip('/')}{path}"


def _error_from_response(resp: httpx.Response) -> str:
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    return json.dumps({"ok": False, "status_code": resp.status_code, "error": detail}, ensure_ascii=False)


def _auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def _ok(data: Any) -> str:
    return json.dumps({"ok": True, **(data if isinstance(data, dict) else {"data": data})}, ensure_ascii=False)


def _request(
    method: str,
    path: str,
    *,
    access_token: str | None = None,
    json_body: dict[str, Any] | None = None,
) -> str:
    headers = _auth_headers(access_token) if access_token else None
    with httpx.Client(timeout=15.0) as client:
        resp = client.request(method, _api(path), headers=headers, json=json_body)
    if resp.status_code >= 400:
        return _error_from_response(resp)
    if resp.status_code == 204 or not resp.content:
        return json.dumps({"ok": True}, ensure_ascii=False)
    body = resp.json()
    if isinstance(body, list):
        return json.dumps({"ok": True, "items": body}, ensure_ascii=False)
    if isinstance(body, dict):
        return _ok(body)
    return json.dumps({"ok": True, "data": body}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Tools — Users
# ---------------------------------------------------------------------------


@mcp.tool()
def register_user(
    username: str,
    email: str,
    password: str,
    display_name: str | None = None,
) -> str:
    """注册新用户。对应 POST /api/users/register。"""
    payload: dict[str, Any] = {"username": username, "email": email, "password": password}
    if display_name:
        payload["display_name"] = display_name
    return _request("POST", "/api/users/register", json_body=payload)


@mcp.tool()
def login_user(username: str, password: str) -> str:
    """用户登录，返回 JWT access_token。对应 POST /api/users/login。"""
    return _request("POST", "/api/users/login", json_body={"username": username, "password": password})


@mcp.tool()
def get_current_user(access_token: str) -> str:
    """获取当前登录用户信息。对应 GET /api/users/me。"""
    return _request("GET", "/api/users/me", access_token=access_token)


@mcp.tool()
def update_user_profile(
    access_token: str,
    email: str | None = None,
    display_name: str | None = None,
    bio: str | None = None,
    password: str | None = None,
) -> str:
    """更新当前用户个人信息。对应 PATCH /api/users/me。"""
    payload: dict[str, Any] = {}
    if email is not None:
        payload["email"] = email
    if display_name is not None:
        payload["display_name"] = display_name
    if bio is not None:
        payload["bio"] = bio
    if password is not None:
        payload["password"] = password
    if not payload:
        return json.dumps({"ok": False, "error": "No fields to update"}, ensure_ascii=False)
    return _request("PATCH", "/api/users/me", access_token=access_token, json_body=payload)


# ---------------------------------------------------------------------------
# Tools — Bills
# ---------------------------------------------------------------------------


@mcp.tool()
def create_bill(
    access_token: str,
    title: str,
    amount: float,
    category: str | None = None,
    note: str | None = None,
    spent_at: str | None = None,
) -> str:
    """创建自己的账单。对应 POST /api/bills。spent_at 格式 YYYY-MM-DD。"""
    payload: dict[str, Any] = {"title": title, "amount": amount}
    if category is not None:
        payload["category"] = category
    if note is not None:
        payload["note"] = note
    if spent_at is not None:
        payload["spent_at"] = spent_at
    return _request("POST", "/api/bills", access_token=access_token, json_body=payload)


@mcp.tool()
def list_my_bills(access_token: str) -> str:
    """读取自己的全部账单。对应 GET /api/bills。"""
    return _request("GET", "/api/bills", access_token=access_token)


@mcp.tool()
def list_shared_bills(access_token: str) -> str:
    """读取别人分享给自己的账单。对应 GET /api/bills/shared-with-me。"""
    return _request("GET", "/api/bills/shared-with-me", access_token=access_token)


@mcp.tool()
def get_bill(access_token: str, bill_id: int) -> str:
    """读取单条账单（自己的或分享给自己的）。对应 GET /api/bills/{id}。"""
    return _request("GET", f"/api/bills/{bill_id}", access_token=access_token)


@mcp.tool()
def update_bill(
    access_token: str,
    bill_id: int,
    title: str | None = None,
    amount: float | None = None,
    category: str | None = None,
    note: str | None = None,
    spent_at: str | None = None,
) -> str:
    """更新自己的账单。对应 PATCH /api/bills/{id}。"""
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title
    if amount is not None:
        payload["amount"] = amount
    if category is not None:
        payload["category"] = category
    if note is not None:
        payload["note"] = note
    if spent_at is not None:
        payload["spent_at"] = spent_at
    if not payload:
        return json.dumps({"ok": False, "error": "No fields to update"}, ensure_ascii=False)
    return _request("PATCH", f"/api/bills/{bill_id}", access_token=access_token, json_body=payload)


@mcp.tool()
def delete_bill(access_token: str, bill_id: int) -> str:
    """删除自己的账单。对应 DELETE /api/bills/{id}。"""
    return _request("DELETE", f"/api/bills/{bill_id}", access_token=access_token)


@mcp.tool()
def share_bill(access_token: str, bill_id: int, username: str) -> str:
    """分享自己的账单给其他用户阅读。对应 POST /api/bills/{id}/share。"""
    return _request(
        "POST",
        f"/api/bills/{bill_id}/share",
        access_token=access_token,
        json_body={"username": username},
    )


@mcp.tool()
def unshare_bill(access_token: str, bill_id: int, username: str) -> str:
    """取消分享。对应 DELETE /api/bills/{id}/share/{username}。"""
    return _request(
        "DELETE",
        f"/api/bills/{bill_id}/share/{username}",
        access_token=access_token,
    )


@mcp.tool()
def like_bill(access_token: str, bill_id: int) -> str:
    """点赞账单（自己的或已分享给自己的）。对应 POST /api/bills/{id}/like。"""
    return _request("POST", f"/api/bills/{bill_id}/like", access_token=access_token)


@mcp.tool()
def unlike_bill(access_token: str, bill_id: int) -> str:
    """取消点赞。对应 DELETE /api/bills/{id}/like。"""
    return _request("DELETE", f"/api/bills/{bill_id}/like", access_token=access_token)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("user://api/health")
def api_health() -> str:
    """User API 健康检查。"""
    with httpx.Client(timeout=10.0) as client:
        try:
            resp = client.get(_api("/health"))
            return json.dumps(
                {"ok": resp.status_code == 200, "body": resp.json()},
                ensure_ascii=False,
            )
        except httpx.HTTPError as exc:
            return json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)


@mcp.resource("user://docs/overview")
def docs_overview() -> str:
    """项目与 MCP 三要素说明（静态资源）。"""
    return (
        "# User + Bill MCP Server\n\n"
        "## Users\n"
        "- POST /api/users/register\n"
        "- POST /api/users/login\n"
        "- GET/PATCH /api/users/me\n\n"
        "## Bills\n"
        "- POST/GET /api/bills\n"
        "- GET /api/bills/shared-with-me\n"
        "- GET/PATCH/DELETE /api/bills/{id}\n"
        "- POST /api/bills/{id}/share\n"
        "- DELETE /api/bills/{id}/share/{username}\n"
        "- POST/DELETE /api/bills/{id}/like\n"
    )


@mcp.resource("user://profile/{access_token}")
def user_profile_resource(access_token: str) -> str:
    """按 token 读取当前用户资料。"""
    return get_current_user(access_token)


@mcp.resource("bill://mine/{access_token}")
def my_bills_resource(access_token: str) -> str:
    """当前用户自己的账单列表。"""
    return list_my_bills(access_token)


@mcp.resource("bill://shared/{access_token}")
def shared_bills_resource(access_token: str) -> str:
    """别人分享给当前用户的账单列表。"""
    return list_shared_bills(access_token)


@mcp.resource("bill://item/{access_token}/{bill_id}")
def bill_item_resource(access_token: str, bill_id: str) -> str:
    """读取单条账单详情。"""
    return get_bill(access_token, int(bill_id))


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def welcome_new_user(username: str, display_name: str | None = None) -> str:
    """生成欢迎新用户的提示词。"""
    name = display_name or username
    return (
        f"你是用户与账单助手。请用友好简洁的中文欢迎「{name}」(username={username})，"
        "说明可以：管理个人资料、记账、分享账单、点赞账单。"
        "不要编造未提供的数据。"
    )


@mcp.prompt()
def help_update_profile(field: str = "display_name") -> str:
    """生成协助用户更新资料的提示词。"""
    return (
        f"用户想更新个人资料字段「{field}」。"
        "请确认已有 access_token，引导提供新值，调用 update_user_profile，再用 get_current_user 核对。"
    )


@mcp.prompt()
def help_create_bill(category: str = "food") -> str:
    """生成协助用户创建账单的提示词。"""
    return (
        f"用户想记一笔类别为「{category}」的账单。"
        "请确认已登录；收集 title、amount，可选 note/spent_at；"
        "调用 create_bill；最后用 list_my_bills 或 get_bill 确认。"
    )


@mcp.prompt()
def help_share_bill(bill_id: int, target_username: str) -> str:
    """生成协助用户分享账单的提示词。"""
    return (
        f"用户想把账单 #{bill_id} 分享给用户「{target_username}」阅读。"
        "请确认当前用户是账单所有者且已登录；调用 share_bill；"
        "再用 get_bill 核对 shared_with 列表。"
    )


@mcp.prompt()
def help_like_bill(bill_id: int) -> str:
    """生成协助用户点赞账单的提示词。"""
    return (
        f"用户想点赞账单 #{bill_id}（可以是自己的，或别人分享给自己的）。"
        "请确认已登录且有读取权限；调用 like_bill；再用 get_bill 核对 like_count / liked_by_me。"
    )


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
    )
