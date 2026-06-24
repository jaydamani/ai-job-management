import uuid
import pytest
import httpx
import asyncpg


CANDIDATE_PAYLOAD = {
    "name": "Alice Smith",
    "email": "alice@example.com",
    "phone": "+1-555-0100",
    "location_preference": "Remote",
    "expected_salary_min": 90000,
    "expected_salary_max": 130000,
    "notice_period_days": 30,
    "source": "LinkedIn",
    "notes": "Strong Python background",
}

JOB_PAYLOAD = {
    "title": "Backend Engineer",
    "description": "FastAPI services.",
    "required_skills": ["Python"],
    "employment_type": "full_time",
    "experience_level": "mid",
    "remote_type": "remote",
}


async def _create_candidate(http_client, auth_headers, overrides=None):
    uid = uuid.uuid4().hex[:8]
    payload = {**CANDIDATE_PAYLOAD, "email": f"cand_{uid}@example.com", **(overrides or {})}
    resp = await http_client.post("/candidates", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_job(http_client, auth_headers):
    resp = await http_client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_candidate(http_client: httpx.AsyncClient, auth_headers: dict, db: asyncpg.Connection):
    uid = uuid.uuid4().hex[:8]
    payload = {**CANDIDATE_PAYLOAD, "email": f"cand_{uid}@example.com"}

    resp = await http_client.post("/candidates", json=payload, headers=auth_headers)

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == payload["name"]
    assert body["email"] == payload["email"]
    assert body["expected_salary_min"] == payload["expected_salary_min"]
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body

    row = await db.fetchrow("SELECT name, email, source FROM candidates WHERE id = $1::uuid", body["id"])
    assert row is not None
    assert row["name"] == payload["name"]
    assert row["email"] == payload["email"]
    assert row["source"] == payload["source"]


@pytest.mark.asyncio
async def test_list_candidates(http_client: httpx.AsyncClient, auth_headers: dict):
    await _create_candidate(http_client, auth_headers)
    await _create_candidate(http_client, auth_headers)

    resp = await http_client.get("/candidates", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 2


@pytest.mark.asyncio
async def test_get_candidate(http_client: httpx.AsyncClient, auth_headers: dict):
    created = await _create_candidate(http_client, auth_headers)
    cid = created["id"]

    resp = await http_client.get(f"/candidates/{cid}", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == cid
    assert body["name"] == created["name"]
    assert "applications" in body
    assert isinstance(body["applications"], list)


@pytest.mark.asyncio
async def test_update_candidate(http_client: httpx.AsyncClient, auth_headers: dict, db: asyncpg.Connection):
    created = await _create_candidate(http_client, auth_headers)
    cid = created["id"]

    resp = await http_client.put(f"/candidates/{cid}", json={"name": "Alice Updated", "notice_period_days": 14}, headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Alice Updated"
    assert body["notice_period_days"] == 14
    assert body["email"] == created["email"]

    row = await db.fetchrow("SELECT name, notice_period_days FROM candidates WHERE id = $1::uuid", cid)
    assert row["name"] == "Alice Updated"
    assert row["notice_period_days"] == 14


@pytest.mark.asyncio
async def test_delete_candidate(http_client: httpx.AsyncClient, auth_headers: dict, db: asyncpg.Connection):
    created = await _create_candidate(http_client, auth_headers)
    cid = created["id"]

    resp = await http_client.delete(f"/candidates/{cid}", headers=auth_headers)
    assert resp.status_code == 204

    row = await db.fetchrow("SELECT id FROM candidates WHERE id = $1::uuid", cid)
    assert row is None

    get_resp = await http_client.get(f"/candidates/{cid}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_candidate(http_client: httpx.AsyncClient, auth_headers: dict):
    resp = await http_client.get(f"/candidates/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_application(http_client: httpx.AsyncClient, auth_headers: dict, db: asyncpg.Connection):
    candidate = await _create_candidate(http_client, auth_headers)
    job = await _create_job(http_client, auth_headers)

    resp = await http_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
        headers=auth_headers,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["candidate_id"] == candidate["id"]
    assert body["job_id"] == job["id"]
    assert body["status"] == "applied"
    assert "applied_at" in body
    assert "updated_at" in body

    row = await db.fetchrow(
        "SELECT status, fit_score FROM candidate_job_applications WHERE id = $1::uuid",
        body["id"],
    )
    assert row is not None
    assert row["status"] == "applied"
    assert row["fit_score"] is None


@pytest.mark.asyncio
async def test_duplicate_application_rejected(http_client: httpx.AsyncClient, auth_headers: dict):
    candidate = await _create_candidate(http_client, auth_headers)
    job = await _create_job(http_client, auth_headers)

    await http_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
        headers=auth_headers,
    )

    resp = await http_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_job_candidates(http_client: httpx.AsyncClient, auth_headers: dict):
    job = await _create_job(http_client, auth_headers)
    candidate1 = await _create_candidate(http_client, auth_headers)
    candidate2 = await _create_candidate(http_client, auth_headers)

    for cid in [candidate1["id"], candidate2["id"]]:
        await http_client.post(
            f"/candidates/{cid}/applications",
            json={"job_id": job["id"]},
            headers=auth_headers,
        )

    resp = await http_client.get(f"/jobs/{job['id']}/candidates", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    ids_in_resp = {item["id"] for item in body["data"]}
    assert candidate1["id"] in ids_in_resp
    assert candidate2["id"] in ids_in_resp
