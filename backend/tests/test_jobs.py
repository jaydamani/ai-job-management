import uuid
import pytest
import httpx
import asyncpg


JOB_PAYLOAD = {
    "title": "Senior Python Engineer",
    "description": "Build scalable backend services.",
    "department": "Engineering",
    "location": "Remote",
    "salary_min": 80000,
    "salary_max": 120000,
    "required_skills": ["Python", "FastAPI", "PostgreSQL"],
    "employment_type": "full_time",
    "experience_level": "senior",
    "remote_type": "remote",
}


@pytest.mark.asyncio
async def test_create_job(http_client: httpx.AsyncClient, auth_headers: dict, db: asyncpg.Connection):
    resp = await http_client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == JOB_PAYLOAD["title"]
    assert body["description"] == JOB_PAYLOAD["description"]
    assert body["salary_min"] == JOB_PAYLOAD["salary_min"]
    assert body["salary_max"] == JOB_PAYLOAD["salary_max"]
    assert body["required_skills"] == JOB_PAYLOAD["required_skills"]
    assert body["status"] == "open"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body

    row = await db.fetchrow("SELECT title, status, salary_min FROM jobs WHERE id = $1::uuid", body["id"])
    assert row is not None
    assert row["title"] == JOB_PAYLOAD["title"]
    assert row["status"] == "open"
    assert row["salary_min"] == JOB_PAYLOAD["salary_min"]


@pytest.mark.asyncio
async def test_list_jobs_returns_created_jobs(http_client: httpx.AsyncClient, auth_headers: dict):
    uid = uuid.uuid4().hex[:6]
    for i in range(2):
        await http_client.post("/jobs", json={**JOB_PAYLOAD, "title": f"List Test Job {uid} #{i}"}, headers=auth_headers)

    resp = await http_client.get("/jobs", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "has_more" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 2


@pytest.mark.asyncio
async def test_get_job(http_client: httpx.AsyncClient, auth_headers: dict):
    create_resp = await http_client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    resp = await http_client.get(f"/jobs/{job_id}", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == job_id
    assert body["title"] == JOB_PAYLOAD["title"]


@pytest.mark.asyncio
async def test_update_job(http_client: httpx.AsyncClient, auth_headers: dict, db: asyncpg.Connection):
    create_resp = await http_client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create_resp.json()["id"]

    update = {"title": "Updated Title", "salary_max": 150000}
    resp = await http_client.put(f"/jobs/{job_id}", json=update, headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated Title"
    assert body["salary_max"] == 150000
    assert body["salary_min"] == JOB_PAYLOAD["salary_min"]

    row = await db.fetchrow("SELECT title, salary_max FROM jobs WHERE id = $1::uuid", job_id)
    assert row["title"] == "Updated Title"
    assert row["salary_max"] == 150000


@pytest.mark.asyncio
async def test_close_job(http_client: httpx.AsyncClient, auth_headers: dict, db: asyncpg.Connection):
    create_resp = await http_client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = create_resp.json()["id"]

    resp = await http_client.patch(f"/jobs/{job_id}/close", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "closed"

    row = await db.fetchrow("SELECT status FROM jobs WHERE id = $1::uuid", job_id)
    assert row["status"] == "closed"


@pytest.mark.asyncio
async def test_get_nonexistent_job(http_client: httpx.AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await http_client.get(f"/jobs/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs_filter_by_status(http_client: httpx.AsyncClient, auth_headers: dict):
    uid = uuid.uuid4().hex[:6]

    create_resp = await http_client.post("/jobs", json={**JOB_PAYLOAD, "title": f"Filter Test {uid}"}, headers=auth_headers)
    job_id = create_resp.json()["id"]
    await http_client.patch(f"/jobs/{job_id}/close", headers=auth_headers)

    resp = await http_client.get("/jobs?status=closed", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert all(j["status"] == "closed" for j in data)


@pytest.mark.asyncio
async def test_job_pagination(http_client: httpx.AsyncClient, auth_headers: dict):
    uid = uuid.uuid4().hex[:6]
    for i in range(3):
        await http_client.post("/jobs", json={**JOB_PAYLOAD, "title": f"Page Test {uid} #{i}"}, headers=auth_headers)

    first_page = await http_client.get("/jobs?limit=2", headers=auth_headers)
    assert first_page.status_code == 200
    page1 = first_page.json()
    assert len(page1["data"]) == 2
    assert page1["has_more"] is True
    assert page1["next_cursor"] is not None

    second_page = await http_client.get(f"/jobs?limit=2&cursor={page1['next_cursor']}", headers=auth_headers)
    assert second_page.status_code == 200
    page2 = second_page.json()
    assert len(page2["data"]) >= 1

    first_ids = {j["id"] for j in page1["data"]}
    second_ids = {j["id"] for j in page2["data"]}
    assert first_ids.isdisjoint(second_ids)
