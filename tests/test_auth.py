import pytest
from starlette.testclient import TestClient
from api.app import app
import api.auth as auth

@pytest.fixture
def client():
    return TestClient(app)

def test_auth_me_unauthenticated(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.json()["detail"]

def test_auth_login_invalid_credentials(client):
    res = client.post("/api/auth/login", json={
        "email": "ceo@nimbusdesk.io",
        "password": "WrongPassword123!"
    })
    assert res.status_code == 401
    assert "Invalid executive credentials" in res.json()["detail"]

def test_auth_login_seeded_ceo(client):
    res = client.post("/api/auth/login", json={
        "email": "ceo@nimbusdesk.io",
        "password": "VentureTwin2026!",
        "remember_me": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["authenticated"] is True
    assert data["user"]["email"] == "ceo@nimbusdesk.io"
    assert "token" in data
    assert "vt_session" in res.cookies

    # Test /api/auth/me with cookie
    cookie = res.cookies["vt_session"]
    me_res = client.get("/api/auth/me", cookies={"vt_session": cookie})
    assert me_res.status_code == 200
    assert me_res.json()["user"]["email"] == "ceo@nimbusdesk.io"

    # Test /api/auth/me with Authorization header
    me_hdr = client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
    assert me_hdr.status_code == 200
    assert me_hdr.json()["user"]["email"] == "ceo@nimbusdesk.io"

def test_auth_register_and_logout(client):
    import secrets
    unique_email = f"exec_{secrets.token_hex(4)}@nimbusdesk.io"
    res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "ExecutivePassword123!",
        "full_name": "Jordan Lee"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == unique_email
    assert data["user"]["full_name"] == "Jordan Lee"
    token = data["token"]
    cookie = res.cookies.get("vt_session")

    # Verify session is active
    me_res = client.get("/api/auth/me", cookies={"vt_session": cookie})
    assert me_res.status_code == 200

    # Logout
    logout_res = client.post("/api/auth/logout", cookies={"vt_session": cookie})
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "logged_out"

    # Verify session is now invalidated
    me_after = client.get("/api/auth/me", cookies={"vt_session": cookie})
    assert me_after.status_code == 401

def test_auth_forgot_password(client):
    res = client.post("/api/auth/forgot-password", json={
        "email": "ceo@nimbusdesk.io"
    })
    assert res.status_code == 200
    assert res.json()["status"] == "success"
