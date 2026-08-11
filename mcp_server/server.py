"""
User MCP Server — Streamable HTTP

MCP 三要素演示：
- Tools: 注册 / 登录 / 更新资料 / 查询当前用户
- Resources: 当前用户资料、API 健康状态
- Prompts: 欢迎语、更新资料助手
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
        "这是一个用户管理 MCP Server。可通过 tools 注册、登录、更新个人信息；"
        "可通过 resources 读取当前用户资料；可通过 prompts 生成对话模板。"
        "需要鉴权的操作请先 login_user，再把返回的 access_token 传给后续工具。"
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


# ---------------------------------------------------------------------------
# Tools —— 可执行操作（对应 REST 接口）
# ---------------------------------------------------------------------------


@mcp.tool()
def register_user(
    username: str,
    email: str,
    password: str,
    display_name: str | None = None,
) -> str:
    """注册新用户。对应 POST /api/users/register。"""
    payload: dict[str, Any] = {
        "username": username,
        "email": email,
        "password": password,
    }
    if display_name:
        payload["display_name"] = display_name

    with httpx.Client(timeout=15.0) as client:
        resp = client.post(_api("/api/users/register"), json=payload)

    if resp.status_code >= 400:
        return _error_from_response(resp)
    return json.dumps({"ok": True, "user": resp.json()}, ensure_ascii=False)


@mcp.tool()
def login_user(username: str, password: str) -> str:
    """用户登录，返回 JWT access_token。对应 POST /api/users/login。"""
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            _api("/api/users/login"),
            json={"username": username, "password": password},
        )

    if resp.status_code >= 400:
        return _error_from_response(resp)
    return json.dumps({"ok": True, **resp.json()}, ensure_ascii=False)


@mcp.tool()
def get_current_user(access_token: str) -> str:
    """获取当前登录用户信息。对应 GET /api/users/me。"""
    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(_api("/api/users/me"), headers=headers)

    if resp.status_code >= 400:
        return _error_from_response(resp)
    return json.dumps({"ok": True, "user": resp.json()}, ensure_ascii=False)


@mcp.tool()
def update_user_profile(
    access_token: str,
    email: str | None = None,
    display_name: str | None = None,
    bio: str | None = None,
    password: str | None = None,
) -> str:
    """更新当前用户个人信息。对应 PATCH /api/users/me。至少提供一个要更新的字段。"""
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

    headers = {"Authorization": f"Bearer {access_token}"}
    with httpx.Client(timeout=15.0) as client:
        resp = client.patch(_api("/api/users/me"), json=payload, headers=headers)

    if resp.status_code >= 400:
        return _error_from_response(resp)
    return json.dumps({"ok": True, "user": resp.json()}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Resources —— 可读数据（URI 寻址）
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
        "# User MCP Server\n\n"
        "## REST API\n"
        "- POST /api/users/register\n"
        "- POST /api/users/login\n"
        "- GET  /api/users/me\n"
        "- PATCH /api/users/me\n\n"
        "## MCP 三要素\n"
        "- Tools: register_user / login_user / get_current_user / update_user_profile\n"
        "- Resources: user://api/health / user://docs/overview / user://profile/{token}\n"
        "- Prompts: welcome_new_user / help_update_profile\n"
    )


@mcp.resource("user://profile/{access_token}")
def user_profile_resource(access_token: str) -> str:
    """按 token 读取当前用户资料（Resource 形式）。"""
    return get_current_user(access_token)


# ---------------------------------------------------------------------------
# Prompts —— 可复用提示词模板
# ---------------------------------------------------------------------------


@mcp.prompt()
def welcome_new_user(username: str, display_name: str | None = None) -> str:
    """生成欢迎新用户的提示词。"""
    name = display_name or username
    return (
        f"你是用户管理系统助手。请用友好简洁的中文欢迎用户「{name}」(username={username})，"
        "并简要说明可以：查看个人信息、更新 display_name/email/bio、修改密码。"
        "不要编造未提供的用户数据。"
    )


@mcp.prompt()
def help_update_profile(field: str = "display_name") -> str:
    """生成协助用户更新资料的提示词。field 例如 display_name / email / bio / password。"""
    return (
        f"用户想更新个人资料字段「{field}」。"
        "请先确认用户已登录并持有 access_token；"
        "然后引导用户提供新值，并调用 update_user_profile 工具完成更新；"
        "最后用 get_current_user 或 user://profile/{token} 核对结果。"
    )


if __name__ == "__main__":
    # Streamable HTTP：客户端访问 http://{host}:{port}/mcp
    mcp.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
    )
