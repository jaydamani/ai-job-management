import uuid
import pytest
import httpx


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
async def test_create_job(authed_client: httpx.AsyncClient):
    resp = await authed_client.post("/jobs", json=JOB_PAYLOAD)

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


@pytest.mark.asyncio
async def test_list_jobs(authed_client: httpx.AsyncClient):
    uid = uuid.uuid4().hex[:6]
    for i in range(2):
        await authed_client.post("/jobs", json={**JOB_PAYLOAD, "title": f"List Test {uid} #{i}"})

    resp = await authed_client.get("/jobs")

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "has_more" in body
    assert "next_cursor" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 2


@pytest.mark.asyncio
async def test_get_job(authed_client: httpx.AsyncClient):
    create_resp = await authed_client.post("/jobs", json=JOB_PAYLOAD)
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    resp = await authed_client.get(f"/jobs/{job_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == job_id
    assert body["title"] == JOB_PAYLOAD["title"]


@pytest.mark.asyncio
async def test_update_job(authed_client: httpx.AsyncClient):
    create_resp = await authed_client.post("/jobs", json=JOB_PAYLOAD)
    job_id = create_resp.json()["id"]

    resp = await authed_client.put(f"/jobs/{job_id}", json={"title": "Updated Title", "salary_max": 150000})

    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Updated Title"
    assert body["salary_max"] == 150000
    assert body["salary_min"] == JOB_PAYLOAD["salary_min"]


@pytest.mark.asyncio
async def test_close_job(authed_client: httpx.AsyncClient):
    create_resp = await authed_client.post("/jobs", json=JOB_PAYLOAD)
    job_id = create_resp.json()["id"]

    resp = await authed_client.patch(f"/jobs/{job_id}/close")

    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_get_nonexistent_job(authed_client: httpx.AsyncClient):
    resp = await authed_client.get(f"/jobs/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_jobs_filter_by_status(authed_client: httpx.AsyncClient):
    uid = uuid.uuid4().hex[:6]
    create_resp = await authed_client.post("/jobs", json={**JOB_PAYLOAD, "title": f"Filter Test {uid}"})
    job_id = create_resp.json()["id"]
    await authed_client.patch(f"/jobs/{job_id}/close")

    resp = await authed_client.get("/jobs?status=closed")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    assert all(j["status"] == "closed" for j in data)


@pytest.mark.asyncio
async def test_list_jobs_filter_by_title(authed_client: httpx.AsyncClient):
    uid = uuid.uuid4().hex[:6]
    await authed_client.post("/jobs", json={**JOB_PAYLOAD, "title": f"UniqueTitle_{uid}"})

    resp = await authed_client.get(f"/jobs?title=UniqueTitle_{uid}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 1
    assert any(uid in j["title"] for j in data)


@pytest.mark.asyncio
async def test_job_pagination(authed_client: httpx.AsyncClient):
    uid = uuid.uuid4().hex[:6]
    for i in range(3):
        await authed_client.post("/jobs", json={**JOB_PAYLOAD, "title": f"Page Test {uid} #{i}"})

    first_page = await authed_client.get("/jobs?limit=2")
    assert first_page.status_code == 200
    page1 = first_page.json()
    assert len(page1["data"]) == 2
    assert page1["has_more"] is True
    assert page1["next_cursor"] is not None

    second_page = await authed_client.get(f"/jobs?limit=2&cursor={page1['next_cursor']}")
    assert second_page.status_code == 200
    page2 = second_page.json()
    assert len(page2["data"]) >= 1

    first_ids = {j["id"] for j in page1["data"]}
    second_ids = {j["id"] for j in page2["data"]}
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.asyncio
async def test_list_job_candidates_empty(authed_client: httpx.AsyncClient):
    create_resp = await authed_client.post("/jobs", json=JOB_PAYLOAD)
    job_id = create_resp.json()["id"]

    resp = await authed_client.get(f"/jobs/{job_id}/candidates")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["has_more"] is False
