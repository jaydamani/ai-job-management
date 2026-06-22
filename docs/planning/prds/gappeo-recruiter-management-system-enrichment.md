---
prd: gappeo-recruiter-management-system
enriched_at: "2026-06-23T00:00:00Z"
status: enriched
depth: standard
---

# Enrichment Report: gappeo-recruiter-management-system

**Status:** validated · 81/100
**Stack:** FastAPI · PostgreSQL · React · MinIO · LiteLLM
**Scope:** greenfield · net-new codebase
**Date:** 2026-06-23

---

## Section 01 — DDL

Full PostgreSQL DDL for all five tables, including enum types, constraints, indexes, and the `updated_at` auto-maintenance trigger. Run these in order; enum types must exist before the tables that reference them.

### Enum Types

```sql
-- Employment classification
CREATE TYPE employment_type_enum AS ENUM (
    'full_time', 'part_time', 'contract', 'internship'
);

-- Experience tier
CREATE TYPE experience_level_enum AS ENUM (
    'junior', 'mid', 'senior', 'lead'
);

-- Work arrangement
CREATE TYPE remote_type_enum AS ENUM (
    'onsite', 'hybrid', 'remote'
);

-- Job lifecycle
CREATE TYPE job_status_enum AS ENUM (
    'open', 'closed'
);

-- Application pipeline stage
CREATE TYPE application_status_enum AS ENUM (
    'applied', 'screened', 'interviewed', 'rejected', 'hired'
);
```

### updated_at Trigger Function

```sql
-- Shared function; called by per-table triggers
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### recruiters

```sql
CREATE TABLE recruiters (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email         TEXT         NOT NULL UNIQUE,
    password_hash TEXT         NOT NULL,
    name          TEXT         NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_recruiters_email ON recruiters (email);
```

### refresh_tokens

```sql
CREATE TABLE refresh_tokens (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    recruiter_id  UUID         NOT NULL REFERENCES recruiters(id) ON DELETE CASCADE,
    token_hash    TEXT         NOT NULL,
    expires_at    TIMESTAMPTZ  NOT NULL,
    revoked       BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_recruiter ON refresh_tokens (recruiter_id);
CREATE INDEX idx_refresh_tokens_lookup    ON refresh_tokens (recruiter_id, revoked, expires_at);
```

> **Note:** The `token_hash` column stores a bcrypt hash of the raw refresh token, not the token itself. Lookup is O(n) over the recruiter's active sessions — see Risk #3 and Implementation Note #12.

### jobs

```sql
CREATE TABLE jobs (
    id               UUID                  PRIMARY KEY DEFAULT gen_random_uuid(),
    recruiter_id     UUID                  NOT NULL REFERENCES recruiters(id) ON DELETE CASCADE,
    title            TEXT                  NOT NULL,
    description      TEXT                  NOT NULL,
    department       TEXT,
    location         TEXT,
    salary_min       INTEGER,
    salary_max       INTEGER,
    required_skills  TEXT[]                NOT NULL DEFAULT '{}',
    employment_type  employment_type_enum,
    experience_level experience_level_enum,
    remote_type      remote_type_enum,
    status           job_status_enum       NOT NULL DEFAULT 'open',
    created_at       TIMESTAMPTZ           NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ           NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_salary_range CHECK (
        salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max
    )
);

-- Filtered list query: WHERE recruiter_id = $1 AND status = $2
CREATE INDEX idx_jobs_recruiter_status ON jobs (recruiter_id, status);

-- Partial-match title filter (ILIKE '%term%') benefits from GIN trigram
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_jobs_title_trgm ON jobs USING GIN (title gin_trgm_ops);

-- GIN on required_skills for ANY/ALL array operators
CREATE INDEX idx_jobs_skills_gin ON jobs USING GIN (required_skills);

CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### candidates

```sql
CREATE TABLE candidates (
    id                    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    recruiter_id          UUID         NOT NULL REFERENCES recruiters(id) ON DELETE CASCADE,
    name                  TEXT         NOT NULL,
    email                 TEXT         NOT NULL,
    phone                 TEXT,
    location_preference   TEXT,
    linkedin_url          TEXT,
    portfolio_url         TEXT,
    github_url            TEXT,
    expected_salary_min   INTEGER,
    expected_salary_max   INTEGER,
    notice_period_days    INTEGER,
    earliest_joining_date DATE,
    source                TEXT,
    referred_by           TEXT,
    notes                 TEXT,
    resume_s3_key         TEXT,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_expected_salary CHECK (
        expected_salary_min IS NULL OR expected_salary_max IS NULL OR
        expected_salary_min <= expected_salary_max
    ),
    CONSTRAINT chk_notice_period CHECK (notice_period_days IS NULL OR notice_period_days >= 0)
);

CREATE INDEX idx_candidates_recruiter ON candidates (recruiter_id);

-- Uniqueness per recruiter, not globally (same candidate can apply via two recruiters)
CREATE UNIQUE INDEX idx_candidates_email_recruiter ON candidates (recruiter_id, email);

CREATE TRIGGER trg_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### candidate_job_applications

```sql
CREATE TABLE candidate_job_applications (
    id               UUID                     PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id     UUID                     NOT NULL REFERENCES candidates(id) ON DELETE CASCADE,
    job_id           UUID                     NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status           application_status_enum  NOT NULL DEFAULT 'applied',
    fit_score        INTEGER                  CHECK (fit_score BETWEEN 0 AND 100),
    fit_explanation  TEXT,
    ai_parsed_resume JSONB,
    interview_notes  TEXT,
    applied_at       TIMESTAMPTZ              NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ              NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_candidate_job UNIQUE (candidate_id, job_id)
);

-- Sorted candidate list for a job: ORDER BY fit_score DESC NULLS LAST
CREATE INDEX idx_apps_job_fitscore ON candidate_job_applications (job_id, fit_score DESC NULLS LAST);

-- Cascade-safe lookup by candidate
CREATE INDEX idx_apps_candidate ON candidate_job_applications (candidate_id);

-- GIN on ai_parsed_resume for JSON key lookups
CREATE INDEX idx_apps_parsed_resume_gin ON candidate_job_applications USING GIN (ai_parsed_resume);

CREATE TRIGGER trg_apps_updated_at
    BEFORE UPDATE ON candidate_job_applications
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

---

## Section 02 — API Contract

All authenticated routes return `401` if the Authorization header is absent or the token is expired. Ownership violations return `404` (not `403`) to avoid resource enumeration. Pagination uses opaque cursor strings — base64-encoded composite of `created_at|id` (or `fit_score|applied_at|id` for the sorted candidates list).

### Auth

| Method | Path | Auth | Request | Response | Codes |
|--------|------|------|---------|----------|-------|
| POST | `/auth/register` | N | `{ email, password, name }` | `{ id, email, name, created_at }` | `201` · `409` email taken · `422` validation |
| POST | `/auth/login` | N | `{ email, password }` | `{ access_token, refresh_token, token_type: "bearer", expires_in: 900 }` | `200` · `401` bad creds |
| POST | `/auth/refresh` | N | `{ refresh_token }` | `{ access_token, refresh_token, token_type: "bearer", expires_in: 900 }` | `200` · `401` revoked/expired |
| POST | `/auth/logout` | Y | `{ refresh_token }` | `{ message: "Logged out" }` | `200` · `401` |

### Jobs

| Method | Path | Auth | Request / Params | Response | Codes |
|--------|------|------|------------------|----------|-------|
| GET | `/jobs` | Y | Query: `cursor?` `limit?=20` `status?` `title?` `department?` `location?` `employment_type?` `experience_level?` `remote_type?` | `{ data: [Job], next_cursor, has_more }` | `200` · `401` |
| POST | `/jobs` | Y | `{ title*, description*, department?, location?, salary_min?, salary_max?, required_skills?, employment_type?, experience_level?, remote_type? }` | Full `Job` object | `201` · `422` |
| GET | `/jobs/{id}` | Y | — | Full `Job` object | `200` · `404` |
| PUT | `/jobs/{id}` | Y | Any writable Job fields | Updated `Job` object | `200` · `404` · `422` |
| PATCH | `/jobs/{id}/close` | Y | — | `{ id, status: "closed", updated_at }` | `200` · `404` |

### Candidates

| Method | Path | Auth | Request / Params | Response | Codes |
|--------|------|------|------------------|----------|-------|
| GET | `/candidates` | Y | Query: `cursor?` `limit?=20` | `{ data: [Candidate], next_cursor, has_more }` | `200` |
| POST | `/candidates` | Y | `{ name*, email*, phone?, location_preference?, linkedin_url?, portfolio_url?, github_url?, expected_salary_min?, expected_salary_max?, notice_period_days?, earliest_joining_date?, source?, referred_by?, notes? }` | Full `Candidate` object | `201` · `422` |
| GET | `/candidates/{id}` | Y | — | `Candidate` + embedded `applications: [ApplicationSummary]` | `200` · `404` |
| PUT | `/candidates/{id}` | Y | Any writable Candidate fields | Updated `Candidate` object | `200` · `404` |
| DELETE | `/candidates/{id}` | Y | — | `{ message: "Deleted" }` | `204` · `404` |
| POST | `/candidates/{id}/resume` | Y | `multipart/form-data` · field: `file` · max 5 MB | `{ resume_s3_key, ai_status: "processing"\|"complete"\|"failed", parsed_resume?, fit_score?, fit_explanation? }` | `200` · `400` non-PDF/oversize · `404` |
| POST | `/candidates/{id}/applications` | Y | `{ job_id* }` | Full `Application` object | `201` · `404` job not found · `409` already applied |

### Jobs → Candidates & Applications

| Method | Path | Auth | Request / Params | Response | Codes |
|--------|------|------|------------------|----------|-------|
| GET | `/jobs/{id}/candidates` | Y | Query: `cursor?` `limit?=20` | `{ data: [CandidateWithApplication], next_cursor, has_more }` sorted `fit_score DESC NULLS LAST` | `200` · `404` |
| PATCH | `/applications/{id}/status` | Y | `{ status* }` (applied\|screened\|interviewed\|rejected\|hired) | Updated `Application` object | `200` · `404` · `422` |

**Pagination cursor encoding:** For `GET /jobs` and `GET /candidates`, the cursor encodes `base64(created_at_iso + "|" + id)`. For `GET /jobs/{id}/candidates`, the cursor encodes `base64(fit_score + "|" + applied_at_iso + "|" + id)` to handle ties in fit_score. All cursors are opaque to the client.

---

## Section 03 — AI Prompt Design

Both AI calls use LiteLLM with `response_format={"type": "json_object"}` (JSON mode). The system prompt enforces schema discipline; the user prompt injects the runtime data. Both prompts include an explicit null fallback instruction and a "return only JSON" directive to suppress prose preamble, which some models still emit even in JSON mode.

### Resume Parsing — System Prompt

```
You are a resume data extractor. Your only job is to read raw resume text and return a single valid JSON object — no preamble, no explanation, no markdown fences.

Return exactly this schema:
{
  "name":                  string | null,
  "email":                 string | null,
  "phone":                 string | null,
  "current_title":         string | null,
  "current_company":       string | null,
  "summary":               string | null,
  "skills":                string[],
  "experience": [
    {
      "title":       string | null,
      "company":     string | null,
      "duration":    string | null,
      "description": string | null
    }
  ],
  "education": [
    {
      "degree":      string | null,
      "institution": string | null,
      "year":        string | null
    }
  ],
  "total_experience_years": number | null
}

Rules:
- If a field cannot be determined from the text, set it to null.
- skills and experience and education must always be arrays (empty array if no data found).
- total_experience_years must be a number (float acceptable), not a string.
- Do not invent or infer information not present in the text.
- Return only the JSON object, starting with { and ending with }.
```

### Resume Parsing — User Prompt Template

```
Extract structured data from the following resume text:

--- RESUME TEXT START ---
{resume_text}
--- RESUME TEXT END ---
```

### Fit Scoring — System Prompt

```
You are a technical recruiter evaluating candidate-job fit. Your only job is to return a single valid JSON object — no preamble, no explanation, no markdown fences.

Scoring rubric:
- Use the job description and required_skills array as the primary scoring criteria.
- Score 0–100: 0 means no relevant match, 100 means exact fit on all criteria.
- strengths: skills or experiences where the candidate clearly meets or exceeds the role.
- gaps: required skills or experience levels the candidate appears to lack.
- explanation: 2–4 concise sentences summarizing the overall fit. Do not repeat the score numerically in the explanation.

Return exactly this schema:
{
  "score":       number,
  "explanation": string,
  "strengths":   string[],
  "gaps":        string[]
}

Rules:
- score must be an integer between 0 and 100 inclusive.
- strengths and gaps must always be arrays (empty array if none).
- explanation must be 2–4 sentences.
- If the candidate data is too sparse to score, return score: 0 and explain why in the explanation field.
- Return only the JSON object, starting with { and ending with }.
```

### Fit Scoring — User Prompt Template

```
Evaluate this candidate's fit for the job below.

--- JOB DESCRIPTION ---
Title: {job_title}
Department: {job_department}
Description: {job_description}
Required skills: {required_skills_comma_separated}
Experience level: {experience_level}
Employment type: {employment_type}

--- CANDIDATE PROFILE ---
Name: {candidate_name}
Current title: {current_title}
Summary: {summary}
Total experience: {total_experience_years} years
Skills: {candidate_skills_comma_separated}
Experience:
{experience_bullet_list}
Education:
{education_bullet_list}
--- END ---
```

### LiteLLM Integration (Python) — Multimodal PDF

PDF bytes are sent directly to the model as a base64 `document` content block. No text extraction step. This natively handles image-only (scanned) PDFs.

```python
import litellm
import json
import base64
from app.config import settings

async def call_ai_json_with_pdf(system_prompt: str, user_text: str, pdf_bytes: bytes) -> dict:
    """
    Sends the PDF as a base64 document content block (Claude multimodal).
    Falls back to text-only if model is not Claude (non-Claude providers don't
    support the document type — provider detection via settings.AI_MODEL prefix).
    """
    is_claude = settings.AI_MODEL.startswith("claude")

    if is_claude:
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        user_content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_b64,
                },
            },
            {"type": "text", "text": user_text},
        ]
    else:
        # Non-Claude: fall back to pdfplumber text extraction
        import pdfplumber
        from io import BytesIO
        text = _extract_pdf_text(pdf_bytes)   # see Implementation Note #11
        user_content = f"{user_text}\n\n{text}"

    response = await litellm.acompletion(
        model=settings.AI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ],
        response_format={"type": "json_object"},
        max_tokens=2048,
        temperature=0.1,
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise AIServiceError(f"Model returned non-JSON: {raw[:200]}") from e


# Resume parsing — passes raw PDF bytes
async def parse_resume(pdf_bytes: bytes) -> dict:
    return await call_ai_json_with_pdf(
        RESUME_SYSTEM_PROMPT,
        "Extract structured data from this resume.",
        pdf_bytes,
    )


# Fit scoring — uses the parsed resume dict (no PDF needed again)
async def score_fit(job: Job, parsed_resume: dict) -> dict:
    user_prompt = FIT_USER_TEMPLATE.format(
        job_title=job.title,
        job_department=job.department or "Not specified",
        job_description=job.description,
        required_skills_comma_separated=", ".join(job.required_skills),
        experience_level=job.experience_level or "Not specified",
        employment_type=job.employment_type or "Not specified",
        candidate_name=parsed_resume.get("name", "Unknown"),
        current_title=parsed_resume.get("current_title") or "Not specified",
        summary=parsed_resume.get("summary") or "Not provided",
        total_experience_years=parsed_resume.get("total_experience_years") or "Unknown",
        candidate_skills_comma_separated=", ".join(parsed_resume.get("skills", [])),
        experience_bullet_list=_format_experience(parsed_resume.get("experience", [])),
        education_bullet_list=_format_education(parsed_resume.get("education", [])),
    )
    # Fit scoring uses text only — parsed_resume already has extracted data
    response = await litellm.acompletion(
        model=settings.AI_MODEL,
        messages=[
            {"role": "system", "content": FIT_SYSTEM_PROMPT},
            {"role": "user",   "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=1024,
        temperature=0.1,
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise AIServiceError(f"Model returned non-JSON: {raw[:200]}") from e
```

> **Multimodal note:** The `document` content block type with `media_type: application/pdf` is a Claude-specific feature. LiteLLM passes it through to the Anthropic API verbatim. OpenAI/GPT models do not support this — the fallback branch uses `pdfplumber` text extraction for non-Claude models (see Implementation Note #11).

---

## Section 04 — Alembic Migration Strategy

### Migration File List

| File | Approach | Contains |
|------|----------|----------|
| `alembic/env.py` | Manual setup | Import `Base.metadata`, configure `target_metadata`, set `DATABASE_URL` from env, enable `compare_type=True` and `compare_server_defaults=True` |
| `0001_create_enum_types.py` | Manual only | All five `CREATE TYPE … AS ENUM` statements. Alembic autogenerate never detects new enum types — must be hand-authored. Downgrade drops them in reverse order. |
| `0002_create_trigger_function.py` | Manual only | `CREATE OR REPLACE FUNCTION set_updated_at()`. Autogenerate has no trigger awareness — this will never appear in a generated diff. |
| `0003_initial_schema.py` | Autogenerate base, manual fixup | All five tables. Run `alembic revision --autogenerate -m "initial_schema"` after defining all SQLAlchemy models. Review the generated file and add: (1) `CREATE EXTENSION IF NOT EXISTS pg_trgm`, (2) GIN indexes (autogenerate misses `postgresql_using="gin"` for ARRAY columns), (3) composite cursor indexes. |
| `0004_attach_updated_at_triggers.py` | Manual only | Three `CREATE TRIGGER` statements for jobs, candidates, and candidate_job_applications. Autogenerate cannot produce trigger DDL. |

### SQLAlchemy Model Snippets — Non-Trivial Columns

```python
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, Date,
    ARRAY, Enum, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMPTZ
import uuid

# ── Enum types: use native_enum=False for Alembic compat ──────────
# native_enum=True would cause autogenerate to emit CREATE TYPE,
# but Alembic's drop_all during testing will leave orphan types.
# Use native_enum=False for test safety; create types manually in
# migration 0001 for production.
employment_type_enum = Enum(
    "full_time", "part_time", "contract", "internship",
    name="employment_type_enum",
    create_type=False,      # type was created in 0001
)

# ── Job model fragment ────────────────────────────────────────────
class Job(Base):
    __tablename__ = "jobs"

    required_skills = Column(
        ARRAY(String),
        nullable=False,
        server_default="{}"
    )
    employment_type  = Column(employment_type_enum)
    experience_level = Column(experience_level_enum)
    remote_type      = Column(remote_type_enum)
    status           = Column(job_status_enum, nullable=False, server_default="open")
    updated_at       = Column(TIMESTAMPTZ, nullable=False, server_default="now()")

    __table_args__ = (
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max",
            name="chk_salary_range"
        ),
    )


# ── Application model fragment — JSONB ───────────────────────────
class CandidateJobApplication(Base):
    __tablename__ = "candidate_job_applications"

    ai_parsed_resume = Column(JSONB, nullable=True)
    fit_score        = Column(Integer, nullable=True)
    fit_explanation  = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("fit_score BETWEEN 0 AND 100", name="chk_fit_score_range"),
        UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job"),
    )
```

**Alembic caveat — ARRAY columns:** Autogenerate detects `ARRAY(String)` columns correctly for create/drop, but will not detect changes to the element type. If you change `ARRAY(String)` to `ARRAY(Text)`, write the ALTER manually. Additionally, GIN indexes on ARRAY columns require `postgresql_using="gin"` in the index definition — autogenerate will emit a btree index unless this is explicitly set.

---

## Section 05 — Project Structure

```
gappeo/
├── .env.example                   # all required env vars with placeholder values
├── .gitignore
├── docker-compose.yml              # backend, frontend, nginx, postgres, minio
│
├── nginx/
│   └── nginx.conf                 # /api → backend:8000, / → frontend:3000
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt            # fastapi uvicorn sqlalchemy alembic pydantic-settings
│   │                               # python-jose passlib[bcrypt] litellm
│   │                               # boto3 python-magic python-multipart
│   │                               # pdfplumber  (fallback for non-Claude models only)
│   ├── alembic/
│   │   ├── env.py                 # imports Base.metadata; reads DATABASE_URL from env
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 0001_create_enum_types.py
│   │       ├── 0002_create_trigger_function.py
│   │       ├── 0003_initial_schema.py
│   │       └── 0004_attach_updated_at_triggers.py
│   └── app/
│       ├── main.py                # FastAPI app init, router registration, CORS, lifespan
│       ├── config.py              # pydantic-settings Settings class; reads all env vars
│       ├── database.py            # SQLAlchemy engine + AsyncSession factory
│       ├── deps.py                # FastAPI Depends: get_db, get_current_recruiter
│       │
│       ├── models/                # SQLAlchemy ORM models
│       │   ├── __init__.py
│       │   ├── base.py            # declarative Base
│       │   ├── recruiter.py
│       │   ├── refresh_token.py
│       │   ├── job.py
│       │   ├── candidate.py
│       │   └── application.py
│       │
│       ├── schemas/               # Pydantic v2 schemas (request + response)
│       │   ├── __init__.py
│       │   ├── auth.py            # RegisterRequest, LoginRequest, TokenResponse
│       │   ├── job.py             # JobCreate, JobUpdate, JobResponse, JobListResponse
│       │   ├── candidate.py       # CandidateCreate, CandidateUpdate, CandidateResponse
│       │   ├── application.py     # ApplicationCreate, ApplicationResponse, StatusUpdate
│       │   └── pagination.py      # PaginatedResponse[T], cursor encode/decode helpers
│       │
│       ├── api/                   # FastAPI routers
│       │   ├── __init__.py
│       │   ├── auth.py            # /auth/register, /login, /refresh, /logout
│       │   ├── jobs.py            # /jobs CRUD + /jobs/{id}/close + /jobs/{id}/candidates
│       │   ├── candidates.py      # /candidates CRUD + /candidates/{id}/resume + /applications
│       │   └── applications.py    # PATCH /applications/{id}/status
│       │
│       └── services/              # Business logic (no HTTP layer)
│           ├── __init__.py
│           ├── auth_service.py    # register, login, refresh, logout, token helpers
│           ├── job_service.py     # create/edit/close/list/get with ownership checks
│           ├── candidate_service.py  # CRUD, link-to-job, delete cascade
│           ├── resume_service.py  # upload → validate → MinIO → extract text → AI
│           ├── ai_service.py      # call_ai_json, parse_resume, score_fit
│           └── storage_service.py # boto3 MinIO client, upload_file, get_presigned_url
│
└── frontend/
    ├── Dockerfile
    ├── package.json               # react react-dom typescript @tanstack/react-query axios
    │                               # react-router-dom react-hook-form zod
    ├── vite.config.ts
    ├── tsconfig.json
    └── src/
        ├── main.tsx               # ReactDOM.createRoot, QueryClientProvider, RouterProvider
        ├── router.tsx             # createBrowserRouter, protected route wrapper
        │
        ├── api/
        │   ├── client.ts          # axios instance with baseURL + request/response interceptors
        │   ├── auth.ts            # register, login, refresh, logout API calls
        │   ├── jobs.ts            # getJobs, createJob, updateJob, closeJob, getJobCandidates
        │   └── candidates.ts      # getCandidates, createCandidate, uploadResume, updateStatus
        │
        ├── hooks/
        │   ├── useAuth.ts         # login/logout + token storage in memory (no localStorage)
        │   ├── useJobs.ts         # useInfiniteQuery wrapper for /jobs with filter params
        │   ├── useCandidates.ts   # useInfiniteQuery for /candidates and /jobs/{id}/candidates
        │   └── useResumeUpload.ts # useMutation for multipart upload with progress state
        │
        ├── types/
        │   └── index.ts           # TypeScript interfaces: Job, Candidate, Application, User
        │
        ├── pages/
        │   ├── LoginPage.tsx      # login form; redirects to /jobs on success
        │   ├── RegisterPage.tsx   # register form
        │   ├── JobsPage.tsx       # job list + filters toolbar + infinite scroll
        │   ├── JobDetailPage.tsx  # job info + candidate list for job + add candidate
        │   ├── JobFormPage.tsx    # create/edit job form (shared, mode via route)
        │   ├── CandidatesPage.tsx # all candidates list for recruiter
        │   └── CandidateDetailPage.tsx  # contact info, pipeline selector, resume, AI data
        │
        └── components/
            ├── ProtectedRoute.tsx # redirects to /login if no auth token
            ├── JobCard.tsx        # compact job summary card
            ├── JobFilters.tsx     # filter panel: status/title/dept/location/type dropdowns
            ├── CandidateCard.tsx  # candidate row with fit score badge
            ├── PipelineSelector.tsx  # status dropdown for application pipeline stage
            ├── ResumeUpload.tsx   # drag-drop or click upload, loading state, error state
            ├── AIDataPanel.tsx    # renders ai_parsed_resume + fit_score + explanation
            ├── FitScoreBadge.tsx  # colored score badge (null → "Pending")
            ├── InfiniteList.tsx   # generic wrapper: renders items + IntersectionObserver sentinel
            └── ErrorBoundary.tsx  # React error boundary for route-level crash isolation
```

---

## Section 06 — Key Implementation Notes

**01 — JWT Dependency Injection Pattern**

Define `get_current_recruiter` in `deps.py` as a FastAPI dependency. It reads the `Authorization: Bearer <token>` header via `HTTPBearer()`, decodes the JWT using `python-jose`, and queries the database for the recruiter by the `sub` claim. Raise `HTTPException(401)` on any failure. Inject it into route handlers as `current_user: Recruiter = Depends(get_current_recruiter)`. The dependency is reusable across all protected routes and keeps the route layer clean.

**02 — Cursor-Based Pagination — Composite Cursor Encoding**

For `GET /jobs` and `GET /candidates`, the cursor is `base64url(created_at_iso8601 + "|" + uuid)`. The SQL predicate is `WHERE (created_at, id) < (cursor_ts, cursor_id) ORDER BY created_at DESC, id DESC`. For `GET /jobs/{id}/candidates` (sorted by fit_score), the cursor is `base64url(fit_score_or_NULL + "|" + applied_at_iso + "|" + id)` to break ties deterministically. Encode/decode helpers live in `schemas/pagination.py`; the service layer never sees raw cursor strings.

**03 — Resume Serving — Presigned URLs, Not Proxy**

Do not proxy the PDF through FastAPI. Instead, when the frontend requests a resume, call `storage_service.get_presigned_url(s3_key, expires=3600)` and return the URL. The frontend opens it directly. This avoids streaming large files through the Python process. Locally, MinIO presigned URLs resolve to `http://localhost:9000`; in production they resolve to your S3 bucket. For Docker Compose, set `S3_ENDPOINT_URL=http://minio:9000` for the backend container and `MINIO_EXTERNAL_URL=http://localhost:9000` separately for URL generation so the presigned URL is resolvable by the browser.

**04 — AI Call Pattern — Synchronous Within Request, No Background Task**

For MVP, run the AI calls synchronously within the `POST /candidates/{id}/resume` request using `await litellm.acompletion()`. This is simpler than a background task queue and the tradeoff is explicit: the HTTP response is delayed by AI latency (typically 3–10 seconds for Claude Sonnet). Return the AI results in the upload response body. The PRD already specifies "if AI fails: resume saved, fit_score null, retriable error returned" — implement this as a try/except around the AI call, so the upload always succeeds even if AI fails.

**05 — PDF MIME Validation — python-magic, Not Content-Type Header**

Never trust the `Content-Type` header from the multipart upload — it is client-controlled and trivially spoofed. Use `python-magic` (libmagic binding) to read the first bytes of the uploaded file and detect the actual MIME type. Check that it equals `application/pdf`. If not, return `400`. Install `python-magic-bin` on Windows or ensure `libmagic1` is in the Docker image. Additionally enforce the 5 MB limit by reading `file.size` from the UploadFile before streaming it — `python-multipart` exposes this without reading the full body.

**06 — bcrypt Cost Factor**

Use a cost factor (rounds) of **12** for password hashing. At rounds=12 on a modern server, bcrypt takes ~250–400 ms — slow enough to resist offline brute force, fast enough that login latency is acceptable. Rounds=10 (passlib default) is insufficiently expensive by 2026 standards. Rounds=14+ introduces perceptible login delays. Set this explicitly: `CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)`.

**07 — CORS Configuration — Nginx-Proxied Single Origin**

Because Nginx proxies both `/api/*` and `/*` from the same origin, the browser sees a single origin. In local development without Nginx (backend on `:8000`, frontend on `:5173`), CORS is needed. Configure FastAPI's `CORSMiddleware` with `allow_origins=settings.CORS_ORIGINS` where `CORS_ORIGINS` is an env var (comma-separated list, default `http://localhost:5173`). In production behind Nginx, set `CORS_ORIGINS=""` (empty) so the middleware is effectively disabled. Do not use `allow_origins=["*"]` in production.

**08 — React Query Infinite Scroll — useInfiniteQuery + IntersectionObserver**

Use `useInfiniteQuery` from `@tanstack/react-query`. Set `getNextPageParam` to extract `next_cursor` from the last page's response (return `undefined` when `has_more` is false). The `InfiniteList` component places a sentinel `<div>` at the bottom of the list and attaches an `IntersectionObserver` to it. When the sentinel enters the viewport, call `fetchNextPage()`. Disable the observer while `isFetchingNextPage` is true to prevent double-fires. This pattern applies to both the jobs list and the candidates list.

**09 — Frontend Token Refresh Interceptor**

In `api/client.ts`, attach an axios response interceptor. On a `401` response, check if the failed request is not itself `/auth/refresh` (to avoid loops). If not, call `POST /auth/refresh` with the stored refresh token. On success, update the in-memory access token and retry the original request with the new token. On failure (refresh also returns 401), clear tokens and redirect to `/login`. Store the access token in module-level memory (not localStorage) to avoid XSS exposure; store the refresh token in an httpOnly cookie if possible, otherwise in memory with the understanding that a page reload requires re-login.

**10 — fit_score Null Handling in Frontend Sort**

The backend returns candidates sorted `fit_score DESC NULLS LAST`. The frontend receives them in this order and should preserve it (do not re-sort client-side). In `FitScoreBadge.tsx`, render `null` fit_score as a "Pending" label with a muted style (not a zero score, which would be misleading). In the candidate list, if the engineer wants a visual score bar, use `score ?? 0` only for the bar width but show "Pending" as the label. This distinction matters: a score of 0 is a real result (genuinely no fit), not a missing one.

**11 — PDF Handling — Multimodal First, Text Extraction Fallback**

For Claude models (`AI_MODEL` starts with `claude`): send the raw PDF bytes as a base64 `document` content block in the user message. The model reads the PDF natively — including scanned/image-only PDFs — with no pre-processing step. This eliminates Risk #3 (image-only PDF failure) entirely for Claude.

For non-Claude models (OpenAI, etc.): extract text with `pdfplumber.open(BytesIO(pdf_bytes))` across all pages. If extracted text is fewer than 50 characters, return a `422` with `error_code: "UNSCANNABLE_PDF"` — the model cannot score an image PDF without multimodal support.

`resume_service.py` calls `ai_service.parse_resume(pdf_bytes)` in both cases; the provider detection is entirely inside `ai_service.py`.

**12 — Refresh Token Lookup Strategy**

On `POST /auth/refresh`, the client sends the raw token. To verify it, query all non-revoked, non-expired refresh tokens for the recruiter (determined by decoding the JWT's `sub` claim from the access token sent alongside, or storing recruiter_id in the refresh token JWT itself). Then bcrypt-compare the raw token against each hash. To bound this to O(1) in practice: issue refresh tokens as JWTs containing the `refresh_token_id` (UUID). On refresh, decode the JWT to get the ID, look up the single row by ID, then bcrypt-compare the stored hash. This avoids the O(n) scan entirely.

---

## Section 07 — Risk Flags

### HIGH — AI Latency on Resume Upload — Synchronous Path Blocks

Running both AI calls (parse + score) synchronously within the HTTP request adds 5–15 seconds to the upload response time in the happy path. Under load or API rate limits, this extends further. The user's upload button is blocked for this duration.

**Mitigation:** For MVP, accept this tradeoff with a clear loading state in the UI ("Analyzing resume…"). Post-MVP, move AI calls to a background worker (Celery, ARQ, or FastAPI BackgroundTasks) and poll for results. The PRD's "retriable error" clause supports this evolution.

### HIGH — LiteLLM JSON Mode Reliability — Non-JSON Output

Even with `response_format={"type": "json_object"}`, some models (and some LiteLLM provider backends) still emit markdown fences, preamble text, or truncated JSON on long resumes. The current prompt includes "return only the JSON object, starting with {" but this is a soft instruction, not a hard guarantee.

**Mitigation:** Wrap `json.loads()` in a try/except in `call_ai_json`. Before parsing, strip any content before the first `{` and after the last `}` as a defensive measure. Log the raw response on failure for debugging. Treat a parse failure as a retriable error (store null fields).

### ~~HIGH~~ RESOLVED — Image-Only (Scanned) PDFs

Previously HIGH risk. **Resolved by multimodal approach.** PDF bytes are sent directly to Claude as a `document` content block — the model reads scanned/image-only PDFs natively without text extraction. This risk only applies when `AI_MODEL` is set to a non-Claude provider, in which case the pdfplumber fallback with sparse-text detection applies.

### MEDIUM — MinIO vs. S3 Parity Gaps

MinIO is S3-compatible but not S3-identical. Specific divergences relevant to this project: presigned URL signature behavior differences between MinIO and AWS S3 when `S3_ENDPOINT_URL` is set, bucket policy enforcement differences, and multipart upload behavior on the free MinIO container. Testing against MinIO locally may not catch S3-specific issues until production.

**Mitigation:** Abstract all storage operations behind `storage_service.py`. Test presigned URL generation and file retrieval both locally (MinIO) and against a real S3 bucket in CI. Keep the boto3 client parameterized by `S3_ENDPOINT_URL`.

### MEDIUM — Cursor Pagination Edge Cases — Ties in fit_score

When multiple candidates have the same fit_score, the cursor must encode a deterministic tiebreaker. Using only `fit_score` as the cursor value means that page boundaries can produce duplicates or skip rows when the score value straddles a page boundary.

**Mitigation:** The cursor for `/jobs/{id}/candidates` encodes `fit_score|applied_at|id` (three-field composite). The SQL predicate becomes `WHERE (fit_score, applied_at, id) < ($cursor_score, $cursor_ts, $cursor_id)` using row comparison. This is stable and deterministic even with many tied scores.

### MEDIUM — JWT Secret Rotation — No Mechanism Defined

The PRD specifies a single `JWT_SECRET` env var. Rotating this secret (required if the secret is compromised) immediately invalidates all active access tokens, logging out all users. There is no mechanism for zero-downtime rotation.

**Mitigation:** Accept this for MVP. Post-MVP, add a `JWT_SECRET_PREVIOUS` env var and validate against both secrets during a rotation window. Alternatively, use a short access token lifetime (15 min, as specified) so rotation impact is bounded.

### MEDIUM — bcrypt at O(n) for Refresh Token Lookup Without JWT Wrapping

Naively, verifying a refresh token requires bcrypt-comparing the raw token against every non-revoked token for the recruiter. A recruiter with many active sessions (e.g., logged in from 10 devices) pays O(n) bcrypt cost at refresh time. With rounds=12, each comparison is ~300 ms.

**Mitigation:** Implement the refresh token as a signed JWT containing the `refresh_token_id` UUID (as described in Implementation Note #12). The lookup becomes O(1): decode JWT → get ID → single row query → one bcrypt comparison.

---

## Section 08 — Complexity Estimate

Estimates assume a single mid-level full-stack engineer comfortable with FastAPI, React, and Docker, but new to LiteLLM, MinIO, and Alembic. Sizes are T-shirt: XS (<1 day), S (1-2 days), M (3-4 days), L (5-7 days).

| Module | Size | Rationale |
|--------|------|-----------|
| Auth Module (backend) | **M** | JWT + refresh token + bcrypt + server-side revocation is well-understood but has several moving parts. Refresh token as JWT (to avoid O(n) lookup) adds a design decision. ~3 days. |
| Jobs Module (backend) | **S** | Standard CRUD with cursor pagination and multi-field filtering. The GIN trigram index for title search is the only non-trivial piece. ~2 days. |
| Candidates Module (backend, non-AI) | **S** | CRUD plus the application join table, fit_score sort cursor, and delete cascade. Similar to Jobs. ~2 days. |
| AI Integration | **M** | Two separate AI calls (parse → score), multimodal PDF input for Claude, LiteLLM async calls, error handling for bad JSON, pdfplumber fallback for non-Claude. The latency risk is the main unknown. ~3–4 days including testing with real PDFs. |
| File Upload Pipeline (MinIO) | **S** | python-magic validation, boto3 upload, presigned URL generation. Well-documented. The Docker networking for presigned URL resolution (backend vs. browser endpoint) is the gotcha. ~1–2 days. |
| Frontend — Auth + Jobs | **M** | Login/register forms, token interceptor, job list with filters, infinite scroll, create/edit form. React Hook Form + Zod validation adds time. ~3 days. |
| Frontend — Candidates + AI UI | **M** | Candidate detail with AI data panel, fit score, pipeline selector, resume upload with loading state. More UI states to handle (pending/complete/failed AI). ~3–4 days. |
| Alembic + DB Setup | **S** | Four migration files, manual enum and trigger DDL, autogenerate for tables. Straightforward if the enum caveats are understood upfront. ~1–2 days. |
| Docker / Infra | **S** | Five containers (backend, frontend, nginx, postgres, minio), named volumes, env var wiring, MinIO bucket init script. ~1–2 days, mostly config. |

### Calendar Estimate — Single Mid-Level Engineer

| Scenario | Duration |
|----------|----------|
| Optimistic | 4 weeks |
| **Likely** | **6 weeks** |
| Pessimistic | 9 weeks |

**Assumptions:** Optimistic assumes no significant LiteLLM reliability issues, no scanned-PDF edge cases, and smooth Docker networking for MinIO presigned URLs. Likely adds 2 weeks for debugging real-world PDF failures, AI prompt iteration, and React Query infinite scroll edge cases. Pessimistic adds a further 3 weeks for a decision to refactor the AI call to a background task (if latency is unacceptable in testing) or to add OCR support for scanned PDFs.

### Top 3 Uncertainty Drivers

1. **AI prompt reliability with diverse real-world resumes.** The time needed to iterate on prompts to handle edge cases (multi-page resumes, unusual formats, non-English content, image-heavy PDFs) is the single largest unknown. Budget 3–5 days for prompt iteration alone.

2. **MinIO presigned URL resolution in Docker Compose.** The internal hostname (`minio:9000`) is not reachable by the browser. Getting presigned URLs to resolve correctly for both the backend container and the end-user browser requires a two-endpoint configuration that is not obvious and frequently causes an entire day of debugging.

3. **Decision on synchronous vs. background AI calls.** If the engineer tests the upload flow and finds 10-second response times unacceptable, retrofitting a background task queue is a non-trivial architectural change. This decision should be made explicitly before implementation begins, not after.
