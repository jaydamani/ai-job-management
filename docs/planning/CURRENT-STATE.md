# Current State — Gappeo

**Last updated:** 2026-06-24
**Branch:** master
**Overall status:** Backend complete — all 3 backend modules + infra scaffolded; frontend next

## PRD Status

| File | Status | Score |
|------|--------|-------|
| [gappeo-recruiter-management-system.md](prds/gappeo-recruiter-management-system.md) | ✅ enriched | 81% |
| [gappeo-recruiter-management-system-enrichment.md](prds/gappeo-recruiter-management-system-enrichment.md) | ✅ complete | — |

## Module Build Status

| Module | Status | Notes |
|--------|--------|-------|
| Project scaffold / git | ✅ Complete | FastAPI + SQLAlchemy async + Alembic + all service layers |
| Auth (JWT + refresh tokens) | ✅ Complete | JWT-wrapped refresh token UUID, bcrypt rounds=12, server-side revocation |
| Jobs (CRUD + filter) | ✅ Complete | 7 query filters, cursor pagination, GIN trgm index on title |
| Candidates (CRUD + AI + pipeline) | ✅ Complete | PDF upload, multimodal AI parse/score, fit_score cursor for job candidates |
| Alembic migrations | ✅ Complete | 4 migrations: enums → trigger fn → schema + indexes → triggers |
| Docker / Infra | ✅ Complete | docker-compose, nginx, Dockerfile, .env.example |
| Frontend (React/TS) | ❌ Not started | Next task |
| README.md | ❌ Not started | After frontend |

## Key Architecture Decisions (locked)

- **Auth:** JWT 15-min access + 30-day refresh; refresh stored as bcrypt hash in `refresh_tokens`; token is itself a JWT containing `jti` (UUID) for O(1) lookup + single bcrypt compare
- **Candidate–Job:** Many-to-many via `CandidateJobApplication`; `UNIQUE(candidate_id, job_id)`
- **Pipeline:** applied → screened → interviewed → rejected / hired
- **AI:** LiteLLM, default `claude-sonnet-4-6`; multimodal PDF via base64 `document` block (Claude); pdfplumber fallback (non-Claude); parse + score are separate calls; score 0–100 stored per application
- **Upload:** PDF only, 5 MB, python-magic MIME validation; boto3/S3 throughout; presigned URLs use `MINIO_PUBLIC_URL` client for browser-resolvable links
- **Pagination:** Cursor-based, 20/fetch; `base64(created_at|id)` for jobs/candidates; `base64(fit_score|applied_at|id)` for job candidates
- **Serving:** Nginx (`/api/*` → backend:8000, `/*` → frontend:3000) in Docker Compose; Vite proxy for local dev; CORS for Render
- **Deployment:** Render + Cloudflare R2; MinIO locally only

## Next Action

Scaffold React/TypeScript frontend:
1. `npm create vite@latest frontend -- --template react-ts`
2. Install: `react-router-dom @tanstack/react-query axios react-hook-form zod`
3. Wire `api/client.ts` with refresh interceptor
4. Implement pages: Login → Jobs → Job Detail → Candidates → Candidate Detail
5. Add `frontend/Dockerfile` for Docker Compose
