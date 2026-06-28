import uuid
import pytest
import httpx


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


async def _create_candidate(authed_client, overrides=None):
    uid = uuid.uuid4().hex[:8]
    payload = {**CANDIDATE_PAYLOAD, "email": f"cand_{uid}@example.com", **(overrides or {})}
    resp = await authed_client.post("/candidates", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_job(authed_client):
    resp = await authed_client.post("/jobs", json=JOB_PAYLOAD)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_create_candidate(authed_client: httpx.AsyncClient):
    uid = uuid.uuid4().hex[:8]
    payload = {**CANDIDATE_PAYLOAD, "email": f"cand_{uid}@example.com"}

    resp = await authed_client.post("/candidates", json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == payload["name"]
    assert body["email"] == payload["email"]
    assert body["expected_salary_min"] == payload["expected_salary_min"]
    assert body["notice_period_days"] == payload["notice_period_days"]
    assert body["source"] == payload["source"]
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_list_candidates(authed_client: httpx.AsyncClient):
    await _create_candidate(authed_client)
    await _create_candidate(authed_client)

    resp = await authed_client.get("/candidates")

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "has_more" in body
    assert "next_cursor" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 2


@pytest.mark.asyncio
async def test_get_candidate(authed_client: httpx.AsyncClient):
    created = await _create_candidate(authed_client)
    cid = created["id"]

    resp = await authed_client.get(f"/candidates/{cid}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == cid
    assert body["name"] == created["name"]
    assert "applications" in body
    assert isinstance(body["applications"], list)


@pytest.mark.asyncio
async def test_update_candidate(authed_client: httpx.AsyncClient):
    created = await _create_candidate(authed_client)
    cid = created["id"]

    resp = await authed_client.put(f"/candidates/{cid}", json={"name": "Alice Updated", "notice_period_days": 14})

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Alice Updated"
    assert body["notice_period_days"] == 14
    assert body["email"] == created["email"]


@pytest.mark.asyncio
async def test_delete_candidate(authed_client: httpx.AsyncClient):
    created = await _create_candidate(authed_client)
    cid = created["id"]

    resp = await authed_client.delete(f"/candidates/{cid}")
    assert resp.status_code == 204

    get_resp = await authed_client.get(f"/candidates/{cid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_candidate(authed_client: httpx.AsyncClient):
    resp = await authed_client.get(f"/candidates/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_application(authed_client: httpx.AsyncClient):
    candidate = await _create_candidate(authed_client)
    job = await _create_job(authed_client)

    resp = await authed_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["candidate_id"] == candidate["id"]
    assert body["job_id"] == job["id"]
    assert body["status"] == "applied"
    assert body["fit_score"] is None
    assert body["ai_status"] is None
    assert "applied_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_duplicate_application_rejected(authed_client: httpx.AsyncClient):
    candidate = await _create_candidate(authed_client)
    job = await _create_job(authed_client)

    await authed_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
    )

    resp = await authed_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_application_status(authed_client: httpx.AsyncClient):
    candidate = await _create_candidate(authed_client)
    job = await _create_job(authed_client)

    app_resp = await authed_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
    )
    app_id = app_resp.json()["id"]

    resp = await authed_client.patch(f"/applications/{app_id}/status", json={"status": "screened"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "screened"
    assert body["id"] == app_id


@pytest.mark.asyncio
async def test_list_job_candidates(authed_client: httpx.AsyncClient):
    job = await _create_job(authed_client)
    candidate1 = await _create_candidate(authed_client)
    candidate2 = await _create_candidate(authed_client)

    for cand in [candidate1, candidate2]:
        await authed_client.post(
            f"/candidates/{cand['id']}/applications",
            json={"job_id": job["id"]},
        )

    resp = await authed_client.get(f"/jobs/{job['id']}/candidates")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 2
    ids_in_resp = {item["id"] for item in body["data"]}
    assert candidate1["id"] in ids_in_resp
    assert candidate2["id"] in ids_in_resp


@pytest.mark.asyncio
async def test_job_candidates_have_nested_application(authed_client: httpx.AsyncClient):
    job = await _create_job(authed_client)
    candidate = await _create_candidate(authed_client)
    await authed_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
    )

    resp = await authed_client.get(f"/jobs/{job['id']}/candidates")

    assert resp.status_code == 200
    item = resp.json()["data"][0]
    assert "application" in item
    assert item["application"]["status"] == "applied"
    assert item["application"]["job_id"] == job["id"]


@pytest.mark.asyncio
async def test_rescore_without_resume_returns_400(authed_client: httpx.AsyncClient):
    candidate = await _create_candidate(authed_client)
    job = await _create_job(authed_client)

    app_resp = await authed_client.post(
        f"/candidates/{candidate['id']}/applications",
        json={"job_id": job["id"]},
    )
    app_id = app_resp.json()["id"]

    resp = await authed_client.post(f"/candidates/{candidate['id']}/applications/{app_id}/rescore")

    assert resp.status_code == 400
    assert "resume" in resp.json()["detail"].lower()
