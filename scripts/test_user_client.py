#!/usr/bin/env python3
"""独立测试 User REST API：health / register / login / me / update。"""

from __future__ import annotations

import httpx

from http_helpers import api_base, ensure_api_up, ok, register_and_login


def main() -> int:
    base = api_base()
    print(f"API base: {base}")
    print("=== User API tests ===")

    with httpx.Client(timeout=15.0) as client:
        if not ensure_api_up(client, base):
            return 1

        username, token = register_and_login(client, base, "user")
        headers = {"Authorization": f"Bearer {token}"}

        me = client.get(f"{base}/api/users/me", headers=headers)
        if ok("GET /api/users/me", me, 200) is None:
            return 1

        updated = client.patch(
            f"{base}/api/users/me",
            headers=headers,
            json={"display_name": "User Updated", "bio": "hello from test_user_client"},
        )
        if ok("PATCH /api/users/me", updated, 200) is None:
            return 1

        bad = client.get(f"{base}/api/users/me")
        ok("GET /api/users/me (无 token，期望 401)", bad, 401)

    print(f"All user API checks passed. user={username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
