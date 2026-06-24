import uuid
import pytest
import pytest_asyncio
import httpx
import asyncpg


@pytest.mark.asyncio
async def test_register_success(http_client: httpx.AsyncClient, db: asyncpg.Connection):
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

    row = await db.fetchrow("SELECT email, name FROM recruiters WHERE id = $1::uuid", body["id"])
    assert row is not None
    assert row["email"] == payload["email"]
    assert row["name"] == payload["name"]


@pytest.mark.asyncio
async def test_register_duplicate_email(http_client: httpx.AsyncClient, registered_user: dict):
    payload = {
        "email": registered_user["email"],
        "password": "AnotherPass123!",
        "name": "Duplicate",
    }
    resp = await http_client.post("/auth/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(http_client: httpx.AsyncClient, registered_user: dict, db: asyncpg.Connection):
    resp = await http_client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"

    row = await db.fetchrow(
        "SELECT revoked FROM refresh_tokens WHERE recruiter_id = $1::uuid ORDER BY created_at DESC LIMIT 1",
        registered_user["id"],
    )
    assert row is not None
    assert row["revoked"] is False


@pytest.mark.asyncio
async def test_login_wrong_password(http_client: httpx.AsyncClient, registered_user: dict):
    resp = await http_client.post("/auth/login", json={
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
async def test_token_refresh(http_client: httpx.AsyncClient, auth_tokens: dict):
    resp = await http_client.post("/auth/refresh", json={"refresh_token": auth_tokens["refresh_token"]})

    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["access_token"] != auth_tokens["access_token"]


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(
    http_client: httpx.AsyncClient,
    registered_user: dict,
    db: asyncpg.Connection,
):
    login_resp = await http_client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    access = tokens["access_token"]
    refresh = tokens["refresh_token"]

    logout_resp = await http_client.post(
        "/auth/logout",
        json={"refresh_token": refresh},
        headers={"Authorization": f"Bearer {access}"},
    )
    assert logout_resp.status_code == 200

    row = await db.fetchrow(
        "SELECT revoked FROM refresh_tokens ORDER BY created_at DESC LIMIT 1",
    )
    assert row["revoked"] is True


@pytest.mark.asyncio
async def test_protected_route_requires_auth(http_client: httpx.AsyncClient):
    # FastAPI HTTPBearer returns 403 when Authorization header is absent entirely
    resp = await http_client.get("/jobs")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_protected_route_with_valid_token(http_client: httpx.AsyncClient, auth_headers: dict):
    resp = await http_client.get("/jobs", headers=auth_headers)
    assert resp.status_code == 200
