from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register_login_me_update(client: TestClient) -> None:
    reg = client.post(
        "/api/users/register",
        json={
            "username": "bob_user",
            "email": "bob_user@example.com",
            "password": "secret123",
            "display_name": "Bob",
        },
    )
    assert reg.status_code == 201
    assert reg.json()["username"] == "bob_user"

    login = client.post(
        "/api/users/login",
        json={"username": "bob_user", "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/api/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "bob_user"

    updated = client.patch(
        "/api/users/me",
        headers=headers,
        json={"display_name": "Bobby", "bio": "hello"},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Bobby"
    assert updated.json()["bio"] == "hello"


def test_me_without_token_unauthorized(client: TestClient) -> None:
    resp = client.get("/api/users/me")
    assert resp.status_code == 401


def test_duplicate_username_rejected(client: TestClient) -> None:
    payload = {
        "username": "dup_user",
        "email": "dup1@example.com",
        "password": "secret123",
    }
    assert client.post("/api/users/register", json=payload).status_code == 201
    again = client.post(
        "/api/users/register",
        json={**payload, "email": "dup2@example.com"},
    )
    assert again.status_code == 400
