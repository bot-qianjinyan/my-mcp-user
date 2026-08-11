#!/usr/bin/env python3
"""独立测试 Bill REST API：创建 / 读取 / 更新 / 分享 / 点赞 / 删除。"""

from __future__ import annotations

import httpx

from http_helpers import api_base, ensure_api_up, ok, register_and_login


def main() -> int:
    base = api_base()
    print(f"API base: {base}")
    print("=== Bill API tests ===")

    with httpx.Client(timeout=15.0) as client:
        if not ensure_api_up(client, base):
            return 1

        owner, owner_token = register_and_login(client, base, "owner")
        friend, friend_token = register_and_login(client, base, "friend")
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
        bill = ok("POST /api/bills", created, 201)
        if not isinstance(bill, dict):
            return 1
        bill_id = bill["id"]

        mine = client.get(f"{base}/api/bills", headers=owner_headers)
        if ok("GET /api/bills", mine, 200) is None:
            return 1

        one = client.get(f"{base}/api/bills/{bill_id}", headers=owner_headers)
        if ok(f"GET /api/bills/{bill_id}", one, 200) is None:
            return 1

        updated = client.patch(
            f"{base}/api/bills/{bill_id}",
            headers=owner_headers,
            json={"title": "午餐升级", "amount": "45.00"},
        )
        if ok(f"PATCH /api/bills/{bill_id}", updated, 200) is None:
            return 1

        denied = client.get(f"{base}/api/bills/{bill_id}", headers=friend_headers)
        ok(f"GET /api/bills/{bill_id} (friend before share, expect 403)", denied, 403)

        shared = client.post(
            f"{base}/api/bills/{bill_id}/share",
            headers=owner_headers,
            json={"username": friend},
        )
        if ok(f"POST /api/bills/{bill_id}/share", shared, 200) is None:
            return 1

        readable = client.get(f"{base}/api/bills/{bill_id}", headers=friend_headers)
        if ok(f"GET /api/bills/{bill_id} (friend after share)", readable, 200) is None:
            return 1

        shared_list = client.get(f"{base}/api/bills/shared-with-me", headers=friend_headers)
        if ok("GET /api/bills/shared-with-me", shared_list, 200) is None:
            return 1

        like_own = client.post(f"{base}/api/bills/{bill_id}/like", headers=owner_headers)
        if ok(f"POST /api/bills/{bill_id}/like (owner)", like_own, 200) is None:
            return 1

        like_friend = client.post(f"{base}/api/bills/{bill_id}/like", headers=friend_headers)
        if ok(f"POST /api/bills/{bill_id}/like (friend)", like_friend, 200) is None:
            return 1

        unlike = client.delete(f"{base}/api/bills/{bill_id}/like", headers=friend_headers)
        if ok(f"DELETE /api/bills/{bill_id}/like", unlike, 200) is None:
            return 1

        unshare = client.delete(
            f"{base}/api/bills/{bill_id}/share/{friend}",
            headers=owner_headers,
        )
        if ok(f"DELETE /api/bills/{bill_id}/share/{friend}", unshare, 200) is None:
            return 1

        deleted = client.delete(f"{base}/api/bills/{bill_id}", headers=owner_headers)
        if ok(f"DELETE /api/bills/{bill_id}", deleted, 200) is None:
            return 1

    print(f"All bill API checks passed. owner={owner}, friend={friend}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
