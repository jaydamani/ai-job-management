# Recruiter Management System

A full-stack recruiter tool where you manage job openings and candidates with AI-powered resume parsing and fit scoring. Built as a take-home assignment.

**Live:** [https://ai-job-management.onrender.com](https://ai-job-management.onrender.com) *(free tier, give it ~30s to wake)*

---

## Running Locally

```bash
git clone https://github.com/jay-damani/gappeo.git
cd gappeo
cp .env.example .env
# Fill in: JWT_SECRET, AI_MODEL, and the key for gemini or any other provider
docker-compose up
```

Open `http://localhost:8080`

> [!NOTE] 
> To avoid S3 setup, the docker compose includes MinIO which provides S3 compatible object storage using local volumes
> 
> To avoid DB setup, the docker compose includes postgres service which spins up a local db.
> 
> For a production deployment, both of these can be replaced using just environment variables
---

## Key Decisions

### Allow multiple applications per candidate

The brief asked for candidates linked to jobs. The obvious move is a foreign key from `candidates` to `jobs`. I didn't do that.

The real shape is many-to-many: For large organisations, it is common to allow applications for different roles (workday does this). If we use a one to many at the start, it will be extremenly painful to migrate as we go further.

```
candidates <-- candidate_job_applications --> jobs
```

`CandidateJobApplication` holds the per-application state: `status`, `fit_score`, `fit_explanation`, `strengths`, `gaps`, `ai_status`, `resume_s3_key`, `interview_notes`. They are not on the candidate row, because they're answers to "how does *this* candidate fit *this* job".

One consequence: A candidate submitting a tailored resume for two different roles can get scored independently for each one.

### Auth — cookies over tokens-in-localStorage

This is one of those things where coding agents are consistently wrong. It always start with local storage for some reason. Local storage is not meant to be secured so, this can cause trouble in later stages.

This is the current strategy:

JWT access tokens (15-minute TTL) and refresh tokens (30-day TTL) are in httpOnly cookies, never in localStorage or returned in response bodies. Two reasons:

1. httpOnly cookies are inaccessible to JavaScript, so XSS can't steal them.
2. Refresh tokens need server-side revocation to support real logout. Storing a bcrypt hash of the token in a `refresh_tokens` table makes it a stateful invalidation check — the hash is computed on every refresh, so a stolen token can be revoked.

The tradeoff is CSRF exposure, which is avoided by setting 
cookies require `Secure=true` and `SameSite=None` which is done by COOKIES_SECURE=TRUE in environment variables.

### AI layer — LiteLLM + structured output + multimodal PDF

Resume parsing needs to return structured data, not prose. The approach:

- **LiteLLM** as the provider abstraction layer. Swap `AI_MODEL` in `.env` to use any provider — currently defaults to Gemini Flash Lite (free tier-friendly), but Claude Sonnet and GPT-4o are drop-in via the same `litellm.acompletion()` call.
- **JSON Schema structured output** (`response_format: {type: "json_schema", strict: true}`) so the model is forced into the exact shape the code expects. No parsing fragility, no prompt-engineering hoping the model closes its code fences.
- **pymupdf for multimodal** — each PDF page is rendered to a PNG at 2× zoom (≈144 DPI) and sent as `image_url` blocks. This handles image-only PDFs (scanned documents) that pdfplumber would miss entirely. It also means the model sees the layout, not just extracted text, which matters for two-column resumes.

The parse and score steps are **separate calls**. This was a deliberate choice: parse once, score many times (against multiple job openings), and rescore cheaply when needed.

### Experience year calculation — overlapping intervals

LLMs hallucinate "3 years total experience" by summing durations naively or using incorrect current date. The fix is to treat each employment record as a time interval, merge overlapping ones, then sum the gaps. A candidate who worked at two companies simultaneously for 2 years has 2 years of experience, not 4.

The AI extracts `start_year`, `start_month`, `end_year`, `end_month` per role as integers. The backend merges intervals server-side and overwrites `total_experience_years` before persisting. The AI's text answer is discarded in favor of the computed value.

### Skill normalization

Raw skills extracted from resumes are messy: "React.js", "ReactJS", "React JS", "react" all mean the same thing. A custom taxonomy (1,300+ entries across programming, data, cloud, project management, design, etc.) normalizes extracted skills at parse time and at filter time. The skills filter uses exact post-normalization matching, which is why `Java` no longer matches `JavaScript`.

### Cursor pagination over offset

Job and candidate lists use cursor-based pagination instead of `LIMIT/OFFSET`. Offset pagination degrades as datasets grow (a `SKIP 10000` still scans 10,000 rows) and produces duplicates/gaps when rows are inserted between pages. The cursor encodes the last-seen `(created_at, id)` tuple, encoded as base64 to keep the API surface clean.

For the job-candidates list (sorted by fit), the cursor encodes `(fit_score, applied_at, id)` so the sort is stable even when scores are equal.

### Serving — one origin, no CORS, in Docker

In Docker Compose, Nginx sits in front of both services on port 80:
- `/api/*` → `backend:8000`
- `/*` → `frontend:3000`

Same origin means no CORS headers needed, no preflight, no cookie `SameSite` drama — identical to how a real production setup would work. Local dev uses Vite's dev proxy for the same effect without Nginx overhead.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + SQLAlchemy 2.0 (async) + Alembic |
| Database | PostgreSQL (GIN index on job title for trigram search) |
| File storage | MinIO locally, S3-compatible (Cloudflare R2 or AWS S3) in production |
| AI | LiteLLM — any provider via env var |
| Frontend | React 19 + TypeScript 6 + Vite 8 |
| Styling | Tailwind CSS 4 |
| State | TanStack Query (server state) + React Context (auth) |
| Auth | httpOnly cookies, JWT, bcrypt |
| Serving | Nginx reverse proxy |
| Deployment | Render (backend Web Service + frontend Static Site) |

---

## Setup Reference

### `.env` keys

| Key | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `JWT_SECRET` | Yes | Long random string for signing JWTs |
| `AI_MODEL` | Yes | LiteLLM model string (e.g. `gemini/gemini-flash-lite-latest`, `claude-sonnet-4-6`, `gpt-4o`) |
| `GEMINI_API_KEY` | If using Gemini | — |
| `ANTHROPIC_API_KEY` | If using Claude | — |
| `OPENAI_API_KEY` | If using OpenAI | — |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | Yes | MinIO: `minioadmin`/`minioadmin` locally |
| `S3_BUCKET` | Yes | Bucket name — `gappeo` locally |
| `S3_ENDPOINT_URL` | Yes | `http://minio:9000` locally; empty for real AWS |
| `MINIO_PUBLIC_URL` | Local only | `http://localhost:9000` — rewrites internal presigned URLs for browser access |
| `CORS_ORIGINS` | Render only | Frontend URL, e.g. `https://gappeo.onrender.com` |
| `COOKIE_SECURE` | Render only | `true` — enables `Secure` + `SameSite=None` for HTTPS cross-origin cookies |
| `VITE_API_URL` | Render only | Backend URL baked into the frontend at build time |

### Render deployment

The backend runs as a Web Service (`uvicorn app.main:app --host 0.0.0.0 --port $PORT`). The frontend is a Static Site with build command `npm run build` and publish directory `dist`. Set `VITE_API_URL` on the static site to the backend's Render URL.

Postgres is Render's managed database. For file storage, any S3-compatible service works (Cloudflare R2, Backblaze B2, real AWS S3) — set the three `AWS_*` vars and omit `S3_ENDPOINT_URL`.

---

## Bonus: Bulk Resume Upload

`POST /jobs/:id/bulk-upload` accepts a multipart form with up to 20 PDF files. The backend parses and scores all resumes concurrently, then returns all candidates ranked by fit score. Candidates and applications are created atomically — partial batch failure rolls back only that candidate, not the entire upload.

---

## What I'd Improve With More Time

**Async AI pipeline.** Right now, resume parsing and scoring block the HTTP request — if the AI call takes 10 seconds, the user waits 10 seconds. A background task queue (Celery + Redis, or just FastAPI's `BackgroundTasks` for a simpler version) would let the upload return immediately, with the client polling or receiving a webhook when scoring completes. The `ai_status` column already exists for exactly this — it's just waiting for the async infrastructure.

**Skill gap recommendations.** The fit score tells you the number; it doesn't tell you what to do. Given the skills already extracted, a third AI call (after parse + score) could suggest interview questions targeting the gaps, or flag whether the gap is a hard blocker vs. a nice-to-have.

**Candidate deduplication.** Nothing prevents the same candidate from being added twice under different jobs. A fuzzy match on email + name at create time would surface likely duplicates before they pollute the pipeline.

**Streaming AI responses.** The multimodal parse step is the slowest part. Streaming tokens to the frontend while parsing would make the latency feel shorter even if the wall-clock time is the same.

**Search.** The current filtering is field-level (skill, status, score range). Full-text search across parsed resume content (using the JSONB `ai_parsed_resume` column + PostgreSQL `tsvector`) would make candidate retrieval much more powerful.
