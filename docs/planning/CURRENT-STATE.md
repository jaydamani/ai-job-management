# Current State — Gappeo

**Last updated:** 2026-06-23
**Branch:** master
**Overall status:** Pre-implementation — PRD enriched, all decisions locked, ready for backend scaffold

## PRD Status

| File | Status | Score |
|------|--------|-------|
| [gappeo-recruiter-management-system.md](prds/gappeo-recruiter-management-system.md) | ✅ enriched | 81% |
| [gappeo-recruiter-management-system-enrichment.md](prds/gappeo-recruiter-management-system-enrichment.md) | ✅ complete | — |

## Module Build Status

| Module | Status |
|--------|--------|
| Project scaffold / git | ❌ Not started |
| Auth (JWT + refresh tokens) | ❌ Not started |
| Jobs (CRUD + filter) | ❌ Not started |
| Candidates (CRUD + AI + pipeline) | ❌ Not started |
| Frontend (React/TS) | ❌ Not started |
| Docker (compose + Dockerfiles + Nginx) | ❌ Not started |
| .env.example + README | ❌ Not started |

## Key Decisions

- **Authz:** Per-recruiter isolation (404 on cross-access)
- **JWT:** 15-min access + refresh token (30-day TTL); revocation via `refresh_tokens` DB table (token stored hashed); refresh token is itself a JWT containing `refresh_token_id` for O(1) lookup
- **Candidate–Job:** Many-to-many via `CandidateJobApplication`; `UNIQUE(candidate_id, job_id)`
- **Pipeline:** applied → screened → interviewed → rejected / hired
- **AI:** LiteLLM abstraction; default `claude-sonnet-4-6`; **multimodal** — PDF bytes sent as base64 `document` content block (no pdfplumber for Claude); pdfplumber fallback for non-Claude providers; two separate calls: parse → score; score 0–100 + explanation + strengths/gaps
- **Upload:** PDF only, 5 MB, server-side python-magic MIME validation; boto3/S3 throughout; `S3_ENDPOINT_URL` redirects to local MinIO container when set, omitted for real AWS S3
- **Pagination:** Cursor-based, 20/fetch; cursor = `base64(created_at|id)`; candidates-per-job cursor = `base64(fit_score|applied_at|id)`
- **Serving:** Nginx reverse proxy — `/api/*` → FastAPI (8000), `/*` → React (3000); used in Docker Compose. Local dev runs services separately with Vite proxy for `/api`. Render: backend Web Service + frontend Static Site (separate URLs); `VITE_API_URL` baked in at build time; CORS needed (`CORS_ORIGINS` env var).
- **Deployment:** Render (app hosting) + Cloudflare R2 (file storage); R2 is S3-compatible — set `S3_ENDPOINT_URL` + R2 credentials in env vars, no code changes needed; Render managed Postgres as add-on; MinIO used locally only

## Next Action

Begin backend scaffold: create FastAPI project structure, SQLAlchemy models, and run the 4 Alembic migration files from the enrichment report (Section 01 DDL + Section 04 migration strategy).
