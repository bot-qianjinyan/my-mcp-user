from __future__ import annotations

from fastapi.testclient import TestClient


def _register_login(client: TestClient, prefix: str) -> tuple[str, dict[str, str]]:
    username = f"{prefix}_bill"
    client.post(
        "/api/users/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "secret123",
            "display_name": prefix,
        },
    )
    login = client.post(
        "/api/users/login",
        json={"username": username, "password": "secret123"},
    )
    token = login.json()["access_token"]
    return username, {"Authorization": f"Bearer {token}"}


def test_bill_crud_share_like(client: TestClient) -> None:
    owner, owner_headers = _register_login(client, "owner")
    friend, friend_headers = _register_login(client, "friend")

    created = client.post(
        "/api/bills",
        headers=owner_headers,
        json={
            "title": "午餐",
            "amount": "32.50",
            "category": "food",
            "note": "cafeteria",
            "spent_at": "2026-08-11",
        },
    )
    assert created.status_code == 201
    bill_id = created.json()["id"]
    assert created.json()["title"] == "午餐"

    mine = client.get("/api/bills", headers=owner_headers)
    assert mine.status_code == 200
    assert len(mine.json()) == 1

    one = client.get(f"/api/bills/{bill_id}", headers=owner_headers)
    assert one.status_code == 200

    updated = client.patch(
        f"/api/bills/{bill_id}",
        headers=owner_headers,
        json={"title": "午餐升级", "amount": "45.00"},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == "45.00"

    denied = client.get(f"/api/bills/{bill_id}", headers=friend_headers)
    assert denied.status_code == 403

    shared = client.post(
        f"/api/bills/{bill_id}/share",
        headers=owner_headers,
        json={"username": friend},
    )
    assert shared.status_code == 200
    assert friend in shared.json()["shared_with"]

    readable = client.get(f"/api/bills/{bill_id}", headers=friend_headers)
    assert readable.status_code == 200

    shared_list = client.get("/api/bills/shared-with-me", headers=friend_headers)
    assert shared_list.status_code == 200
    assert len(shared_list.json()) == 1

    like_owner = client.post(f"/api/bills/{bill_id}/like", headers=owner_headers)
    assert like_owner.status_code == 200
    assert like_owner.json()["liked_by_me"] is True
    assert like_owner.json()["like_count"] == 1

    like_friend = client.post(f"/api/bills/{bill_id}/like", headers=friend_headers)
    assert like_friend.status_code == 200
    assert like_friend.json()["like_count"] == 2

    unlike = client.delete(f"/api/bills/{bill_id}/like", headers=friend_headers)
    assert unlike.status_code == 200
    assert unlike.json()["like_count"] == 1

    unshare = client.delete(
        f"/api/bills/{bill_id}/share/{friend}",
        headers=owner_headers,
    )
    assert unshare.status_code == 200
    assert unshare.json()["shared_with"] == []

    deleted = client.delete(f"/api/bills/{bill_id}", headers=owner_headers)
    assert deleted.status_code == 200
    assert deleted.json()["message"] == "Bill deleted"

    assert owner  # silence unused if renamed later
