#!/usr/bin/env python3
"""独立测试 User + Bill REST API。"""

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


def _register_and_login(client: httpx.Client, base: str, prefix: str) -> tuple[str, str]:
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
    if _ok(f"POST /api/users/register ({prefix})", reg, 201) is None:
        raise SystemExit(1)
    login = client.post(
        f"{base}/api/users/login",
        json={"username": username, "password": password},
    )
    body = _ok(f"POST /api/users/login ({prefix})", login, 200)
    if not isinstance(body, dict) or not body.get("access_token"):
        raise SystemExit(1)
    return username, body["access_token"]


def main() -> int:
    base = settings.api_base_url.rstrip("/")
    print(f"API base: {base}")

    with httpx.Client(timeout=15.0) as client:
        health = client.get(f"{base}/health")
        if _ok("GET /health", health, 200) is None:
            print("API 未启动，请先运行: uvicorn app.main:app --host 127.0.0.1 --port 8000")
            return 1

        owner, owner_token = _register_and_login(client, base, "owner")
        friend, friend_token = _register_and_login(client, base, "friend")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        friend_headers = {"Authorization": f"Bearer {friend_token}"}

        created = client.post(
            f"{base}/api/bills",
            headers=owner_headers,
            json={
                "title": "午餐",
                "amount": "32.50",
                "category": "food",
                "note": "company cafeteria",
                "spent_at": "2026-08-11",
            },
        )
        bill = _ok("POST /api/bills", created, 201)
        if not isinstance(bill, dict):
            return 1
        bill_id = bill["id"]

        mine = client.get(f"{base}/api/bills", headers=owner_headers)
        if _ok("GET /api/bills", mine, 200) is None:
            return 1

        one = client.get(f"{base}/api/bills/{bill_id}", headers=owner_headers)
        if _ok(f"GET /api/bills/{bill_id}", one, 200) is None:
            return 1

        updated = client.patch(
            f"{base}/api/bills/{bill_id}",
            headers=owner_headers,
            json={"title": "午餐升级", "amount": "45.00"},
        )
        if _ok(f"PATCH /api/bills/{bill_id}", updated, 200) is None:
            return 1

        # friend cannot read before share
        denied = client.get(f"{base}/api/bills/{bill_id}", headers=friend_headers)
        _ok(f"GET /api/bills/{bill_id} (friend before share, expect 403)", denied, 403)

        shared = client.post(
            f"{base}/api/bills/{bill_id}/share",
            headers=owner_headers,
            json={"username": friend},
        )
        if _ok(f"POST /api/bills/{bill_id}/share", shared, 200) is None:
            return 1

        readable = client.get(f"{base}/api/bills/{bill_id}", headers=friend_headers)
        if _ok(f"GET /api/bills/{bill_id} (friend after share)", readable, 200) is None:
            return 1

        shared_list = client.get(f"{base}/api/bills/shared-with-me", headers=friend_headers)
        if _ok("GET /api/bills/shared-with-me", shared_list, 200) is None:
            return 1

        like_own = client.post(f"{base}/api/bills/{bill_id}/like", headers=owner_headers)
        if _ok(f"POST /api/bills/{bill_id}/like (owner)", like_own, 200) is None:
            return 1

        like_friend = client.post(f"{base}/api/bills/{bill_id}/like", headers=friend_headers)
        if _ok(f"POST /api/bills/{bill_id}/like (friend)", like_friend, 200) is None:
            return 1

        unlike = client.delete(f"{base}/api/bills/{bill_id}/like", headers=friend_headers)
        if _ok(f"DELETE /api/bills/{bill_id}/like", unlike, 200) is None:
            return 1

        unshare = client.delete(
            f"{base}/api/bills/{bill_id}/share/{friend}",
            headers=owner_headers,
        )
        if _ok(f"DELETE /api/bills/{bill_id}/share/{friend}", unshare, 200) is None:
            return 1

        deleted = client.delete(f"{base}/api/bills/{bill_id}", headers=owner_headers)
        if _ok(f"DELETE /api/bills/{bill_id}", deleted, 200) is None:
            return 1

    print(f"All API checks passed. owner={owner}, friend={friend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
