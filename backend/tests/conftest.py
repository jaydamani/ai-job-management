import uuid
import pytest
import pytest_asyncio
import httpx
import asyncpg

API_BASE = "http://localhost:8080/api"
DB_DSN = "postgresql://gappeo:gappeo@localhost:5432/gappeo"


@pytest_asyncio.fixture(scope="session")
async def http_client():
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def db():
    conn = await asyncpg.connect(DB_DSN)
    yield conn
    await conn.close()


@pytest_asyncio.fixture(scope="session")
async def registered_user(http_client):
    uid = uuid.uuid4().hex[:8]
    email = f"test_{uid}@example.com"
    password = "TestPass123!"
    name = f"Test Recruiter {uid}"
    resp = await http_client.post("/auth/register", json={"email": email, "password": password, "name": name})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return {"id": body["id"], "email": email, "password": password, "name": name}


@pytest_asyncio.fixture(scope="session")
async def auth_tokens(http_client, registered_user):
    resp = await http_client.post("/auth/login", json={
        "email": registered_user["email"],
        "password": registered_user["password"],
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture(scope="session")
def auth_headers(auth_tokens):
    return {"Authorization": f"Bearer {auth_tokens['access_token']}"}
