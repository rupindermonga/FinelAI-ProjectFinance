"""
Shared pytest fixtures for the Finel AI Projects test suite.
Uses an in-memory SQLite DB so tests are fully isolated and fast.
"""
import os, pytest

# Force in-memory SQLite before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-key-not-for-production")
os.environ.setdefault("GEMINI_API_KEY", "fake-key-for-tests")
os.environ.setdefault("UPLOAD_FOLDER", "/tmp/finel_test_uploads")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.database import get_db
from app.main import app


@pytest.fixture(scope="session")
def engine():
    e = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=e)
    return e


@pytest.fixture(scope="function")
def db_session(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_client(client):
    """Client pre-registered and logged in as a test user."""
    client.post("/api/auth/register", json={
        "username": "testuser",
        "email": "test@finel.ai",
        "password": "TestPass123!",
        "org_name": "Test Org",
    })
    resp = client.post("/api/auth/login", data={
        "username": "testuser",
        "password": "TestPass123!",
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
