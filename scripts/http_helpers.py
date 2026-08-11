"""共享的 HTTP 测试小工具。"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings


def api_base() -> str:
    return settings.api_base_url.rstrip("/")


def ok(name: str, resp: httpx.Response, expect: int | set[int]) -> dict | list | str | None:
    expected = {expect} if isinstance(expect, int) else expect
    status = "PASS" if resp.status_code in expected else "FAIL"
    print(f"[{status}] {name} -> HTTP {resp.status_code}")
    try:
        body = resp.json()
    except Exception:
        body = resp.text
        print(f"       body: {body[:200]}")
        return None

    if isinstance(body, dict):
        safe = {k: ("***" if k == "access_token" else v) for k, v in body.items()}
        print(f"       body: {safe}")
    else:
        print(f"       body: {body}")
    return body if resp.status_code in expected else None


def ensure_api_up(client: httpx.Client, base: str) -> bool:
    health = client.get(f"{base}/health")
    if ok("GET /health", health, 200) is None:
        print("API 未启动，请先运行: uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return False
    return True


def register_and_login(client: httpx.Client, base: str, prefix: str) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    password = "secret123"
    reg = client.post(
        f"{base}/api/users/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
            "display_name": prefix,
        },
    )
    if ok(f"POST /api/users/register ({prefix})", reg, 201) is None:
        raise SystemExit(1)
    login = client.post(
        f"{base}/api/users/login",
        json={"username": username, "password": password},
    )
    body = ok(f"POST /api/users/login ({prefix})", login, 200)
    if not isinstance(body, dict) or not body.get("access_token"):
        raise SystemExit(1)
    return username, body["access_token"]
