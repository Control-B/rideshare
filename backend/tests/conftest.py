import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB = Path(__file__).parent / "test.db"
os.environ["MOBILITY_DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["MOBILITY_JWT_SECRET"] = "test-secret-at-least-thirty-two-bytes-long"

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database():
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "demo-pass-123"},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def rider_auth(client: TestClient):
    token = login(client, "rider@example.test")["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def driver_auth(client: TestClient):
    token = login(client, "driver@example.test")["access_token"]
    return {"Authorization": f"Bearer {token}"}
