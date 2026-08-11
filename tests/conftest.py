from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """FastAPI TestClient + 临时 SQLite，不污染 data/users.db。"""
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)

    from app.config import settings

    monkeypatch.setattr(settings, "database_url", url)

    from app import database

    engine = create_engine(url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)

    from app.database import Base, get_db
    from app.main import app

    # Ensure models are registered
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    username = "alice_test"
    client.post(
        "/api/users/register",
        json={
            "username": username,
            "email": "alice_test@example.com",
            "password": "secret123",
            "display_name": "Alice",
        },
    )
    login = client.post(
        "/api/users/login",
        json={"username": username, "password": "secret123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
