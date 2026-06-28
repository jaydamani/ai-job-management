import uuid
import pytest
import pytest_asyncio
import httpx

API_BASE = "http://localhost:8080/api"


@pytest_asyncio.fixture(scope="session")
async def http_client():
    """Unauthenticated client."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def registered_user():
    """Register a recruiter and return credentials. Uses a throwaway client."""
    uid = uuid.uuid4().hex[:8]
    email = f"test_{uid}@example.com"
    password = "TestPass123!"
    name = f"Test Recruiter {uid}"
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        resp = await c.post("/auth/register", json={"email": email, "password": password, "name": name})
        assert resp.status_code == 201, resp.text
        body = resp.json()
    return {"id": body["id"], "email": email, "password": password, "name": name}


@pytest_asyncio.fixture(scope="session")
async def authed_client(registered_user):
    """httpx client pre-logged-in; carries auth cookies for the session."""
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as c:
        resp = await c.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert resp.status_code == 200, resp.text
        yield c
