#!/usr/bin/env python3
"""独立测试 User REST API：health / register / login / me / update。"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings


def _ok(name: str, resp: httpx.Response, expect: int | set[int]) -> dict | list | str | None:
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


def main() -> int:
    base = settings.api_base_url.rstrip("/")
    suffix = uuid.uuid4().hex[:8]
    username = f"api_user_{suffix}"
    password = "secret123"
    email = f"{username}@example.com"

    print(f"API base: {base}")
    print(f"Test user: {username}")

    with httpx.Client(timeout=15.0) as client:
        health = client.get(f"{base}/health")
        if _ok("GET /health", health, 200) is None:
            print("API 未启动，请先运行: uvicorn app.main:app --host 127.0.0.1 --port 8000")
            return 1

        reg = client.post(
            f"{base}/api/users/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "display_name": "API Tester",
            },
        )
        if _ok("POST /api/users/register", reg, 201) is None:
            return 1

        login = client.post(
            f"{base}/api/users/login",
            json={"username": username, "password": password},
        )
        login_body = _ok("POST /api/users/login", login, 200)
        if not isinstance(login_body, dict) or not login_body.get("access_token"):
            return 1

        token = login_body["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get(f"{base}/api/users/me", headers=headers)
        if _ok("GET /api/users/me", me, 200) is None:
            return 1

        updated = client.patch(
            f"{base}/api/users/me",
            headers=headers,
            json={"display_name": "API Tester Updated", "bio": "hello from test_api_client"},
        )
        if _ok("PATCH /api/users/me", updated, 200) is None:
            return 1

        bad = client.get(f"{base}/api/users/me")
        _ok("GET /api/users/me (无 token，期望 401)", bad, 401)

    print("All API checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
