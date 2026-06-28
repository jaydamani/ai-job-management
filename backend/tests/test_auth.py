import uuid
import pytest
import httpx

API_BASE = "http://localhost:8080/api"


@pytest.mark.asyncio
async def test_register_success(http_client: httpx.AsyncClient):
    uid = uuid.uuid4().hex[:8]
    payload = {"email": f"reg_{uid}@example.com", "password": "Pass123!", "name": f"Reg {uid}"}

    resp = await http_client.post("/auth/register", json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == payload["email"]
    assert body["name"] == payload["name"]
    assert "id" in body
    assert "created_at" in body
    assert "password_hash" not in body
    assert resp.cookies.get("access_token") is not None
    assert resp.cookies.get("refresh_token") is not None


@pytest.mark.asyncio
async def test_register_duplicate_email(registered_user: dict):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        resp = await c.post("/auth/register", json={
            "email": registered_user["email"],
            "password": "AnotherPass123!",
            "name": "Duplicate",
        })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(registered_user: dict):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        resp = await c.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == registered_user["email"]
    assert "id" in body
    assert "created_at" in body
    assert resp.cookies.get("access_token") is not None
    assert resp.cookies.get("refresh_token") is not None


@pytest.mark.asyncio
async def test_login_wrong_password(registered_user: dict):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        resp = await c.post("/auth/login", json={
            "email": registered_user["email"],
            "password": "WrongPassword!",
        })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(http_client: httpx.AsyncClient):
    resp = await http_client.post("/auth/login", json={
        "email": "nobody@nowhere.com",
        "password": "Irrelevant123!",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh(registered_user: dict):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        await c.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        old_access = c.cookies.get("access_token")

        resp = await c.post("/auth/refresh")

    assert resp.status_code == 204
    assert resp.cookies.get("access_token") is not None
    assert resp.cookies.get("access_token") != old_access


@pytest.mark.asyncio
async def test_logout_clears_cookies(registered_user: dict):
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        await c.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })

        resp = await c.post("/auth/logout")

    assert resp.status_code == 204
    assert resp.cookies.get("access_token", "") == ""
    assert resp.cookies.get("refresh_token", "") == ""


@pytest.mark.asyncio
async def test_protected_route_requires_auth():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        resp = await c.get("/jobs")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_valid_cookie(authed_client: httpx.AsyncClient):
    resp = await authed_client.get("/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
