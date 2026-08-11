"""L4 — 真传输：经 Streamable HTTP 连接 /mcp 并完成协议握手。"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn
from mcp.client import Client

from mcp_server.server import mcp


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def mcp_http_base_url():
    """在随机端口拉起真实 Streamable HTTP MCP（不依赖本机已启动的 3001）。"""
    port = _free_port()
    app = mcp.streamable_http_app(streamable_http_path="/mcp")
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while time.time() < deadline:
        if server.started:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("Streamable HTTP MCP server failed to start")

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def mcp_http_url(mcp_http_base_url: str) -> str:
    return f"{mcp_http_base_url}/mcp"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_streamable_http_initialize_and_list_tools(mcp_http_url: str) -> None:
    """外面通过 http://host:port/mcp 能按 MCP 协议连上并 list_tools。"""
    async with Client(mcp_http_url) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        assert "login_user" in names
        assert "create_bill" in names

        prompts = await client.list_prompts()
        prompt_names = {p.name for p in prompts.prompts}
        assert "welcome_new_user" in prompt_names

        resources = await client.list_resources()
        uris = {str(r.uri) for r in resources.resources}
        assert "user://docs/overview" in uris


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_streamable_http_can_call_tool_over_http(mcp_http_url: str) -> None:
    """真传输路径上 call_tool 可用（缺参应返回 is_error，证明请求到达 server）。"""
    async with Client(mcp_http_url) as client:
        result = await client.call_tool("create_bill", {})
        assert result.is_error is True


@pytest.mark.e2e
def test_root_path_is_not_mcp_endpoint(mcp_http_base_url: str) -> None:
    """错误路径不应表现为可用的 MCP 端点。"""
    resp = httpx.get(f"{mcp_http_base_url}/", timeout=5.0)
    assert resp.status_code == 404


@pytest.mark.e2e
def test_mcp_path_rejects_plain_get_without_session(mcp_http_url: str) -> None:
    """裸 GET /mcp 不是完整 MCP 会话；应有 HTTP 错误而非连不上。"""
    resp = httpx.get(mcp_http_url, timeout=5.0)
    assert resp.status_code in {400, 405, 406}
