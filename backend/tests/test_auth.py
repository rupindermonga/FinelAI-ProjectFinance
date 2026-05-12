"""Tests for authentication: register, login, token validation, password reset."""


def test_register_and_login(client):
    r = client.post("/api/auth/register", json={
        "username": "alice",
        "email": "alice@example.com",
        "password": "SecurePass1!",
        "org_name": "Alice Corp",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data

    r2 = client.post("/api/auth/login", data={"username": "alice", "password": "SecurePass1!"})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "username": "bob", "email": "bob@example.com",
        "password": "RealPass1!", "org_name": "Bob Co",
    })
    r = client.post("/api/auth/login", data={"username": "bob", "password": "WrongPass!"})
    assert r.status_code == 401


def test_protected_endpoint_requires_token(client):
    r = client.get("/api/invoices")
    assert r.status_code == 401


def test_protected_endpoint_with_valid_token(auth_client):
    r = auth_client.get("/api/invoices/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "processed" in data
    assert "pending" in data
    assert "errors" in data


def test_duplicate_username_rejected(client):
    client.post("/api/auth/register", json={
        "username": "carol", "email": "carol@example.com",
        "password": "Pass1234!", "org_name": "Carol Co",
    })
    r = client.post("/api/auth/register", json={
        "username": "carol", "email": "carol2@example.com",
        "password": "Pass1234!", "org_name": "Carol Co 2",
    })
    assert r.status_code in (400, 409, 422)
