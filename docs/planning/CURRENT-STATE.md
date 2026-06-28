# Current State — Gappeo

**Last updated:** 2026-06-28
**Branch:** master
**Overall status:** WI-001 through WI-005 complete; WI-006 (frontend scaffold) is next (unblocked)

## PRD Status

| File | Status | Score |
|------|--------|-------|
| [gappeo-recruiter-management-system.md](prds/gappeo-recruiter-management-system.md) | ✅ enriched | 81% |
| [gappeo-recruiter-management-system-enrichment.md](prds/gappeo-recruiter-management-system-enrichment.md) | ✅ complete | — |
| [gappeo-frontend.md](prds/gappeo-frontend.md) | ✅ enriched | 93% validated |
| [gappeo-frontend-validation.md](prds/gappeo-frontend-validation.md) | ✅ complete (fourth pass) | — |
| [gappeo-frontend-enrichment.md](prds/gappeo-frontend-enrichment.md) | ✅ complete | — |
| [gappeo-frontend-breakdown.md](prds/gappeo-frontend-breakdown.md) | ✅ complete | 15 WIs |

## Module Build Status

| Module | Status | Notes |
|--------|--------|-------|
| Project scaffold / git | ✅ Complete | FastAPI + SQLAlchemy async + Alembic + all service layers |
| Auth (JWT + cookies) | ✅ Complete | httpOnly cookie auth via WI-002; access_token 15min, refresh_token 30d; server-side revocation |
| Jobs (CRUD + filter) | ✅ Complete | 7 query filters, cursor pagination, GIN trgm index on title |
| Candidates (CRUD + AI + pipeline) | ✅ Complete | PDF upload, multimodal AI parse/score, fit_score cursor; strengths/gaps/ai_status wired; nested response shape done; rescore endpoint added |
| Alembic migrations | ✅ Complete (0001–0004) | Migration 0004 adds strengths/gaps/ai_status to candidate_job_applications |
| Docker / Infra | ✅ Complete | docker-compose, nginx, Dockerfile, .env.example |
| AI service | ✅ Complete | OpenRouter + structured output (json_schema) + multimodal PDF via pymupdf; FIT_SCHEMA returns strengths[] + gaps[] |
| Backend API contract | ✅ Complete | All schemas aligned; strengths/gaps/ai_status wired; nested CandidateWithApplicationResponse; rescore endpoint done (WI-005) |
| **WI-006: Frontend scaffold** | ❌ Not started | Unblocked — `frontend/src/` does not exist; Tailwind, routing, Axios client, AuthContext |
| Frontend pages (WI-007–WI-012) | ❌ Not started | Login/register, jobs list/form, candidates list/add/detail |
| Backend tests | ⚠️ Will break | Test suite uses Authorization header; needs update after cookie migration (WI-013) |
| Frontend tests | ❌ Not started | WI-014 |
| README.md | ❌ Not started | WI-015 |

## Schema Status (post WI-001 through WI-005)

| # | Issue | Work Item | Status |
|---|-------|-----------|--------|
| 1 | `strengths`/`gaps` wired through resume_service → DB | WI-003 | ✅ |
| 2 | `ai_status` persisted on application row (scoring path) | WI-003 | ✅ |
| 3 | `ResumeUploadResponse.parsed_resume` renamed to `ai_parsed_resume` | WI-003 | ✅ |
| 4 | `CandidateWithApplicationResponse` nested `application: {...}` object | WI-004 | ✅ |
| 5 | Resume upload path includes `appId` segment | WI-005 | ✅ |
| 6 | Rescore endpoint added | WI-005 | ✅ |

## Known Gap

When resume parse fails (before scoring), application rows do not receive `ai_status = 'failed'` — they stay null. Response correctly returns `"failed"` but DB row doesn't reflect it. Fix deferred to WI-013.

## Key Architecture Decisions (locked)

- **Auth:** JWT 15-min access + 30-day refresh; refresh stored as bcrypt hash in `refresh_tokens`; tokens in httpOnly cookies (`access_token`, `refresh_token`); no tokens in response body or localStorage
- **Candidate–Job:** Many-to-many via `CandidateJobApplication`; `UNIQUE(candidate_id, job_id)`
- **Pipeline:** applied → screened → interviewed → rejected / hired
- **AI:** LiteLLM → OpenRouter; default `openrouter/anthropic/claude-sonnet-4-5`; multimodal PDF via pymupdf (pages → PNG images → `image_url` blocks); structured output via `json_schema` response format (strict); parse + score are separate calls; score 0–100 stored per application; `ai_status` values: `"complete"` / `"failed"`; `FIT_SCHEMA` returns `strengths[]` + `gaps[]`
- **AI retry:** `POST /candidates/:id/applications/:appId/rescore` — no body; backend re-runs scoring on the stored S3 PDF; no re-upload required
- **Upload:** PDF only, 5 MB, python-magic MIME validation; boto3/S3 throughout; presigned URLs via `get_presigned_url` (1-hour expiry); raw S3 key stored in DB, `resume_url` (presigned) exposed in responses
- **Pagination:** Cursor-based, 20/fetch; `base64(created_at|id)` for jobs/candidates; `base64(fit_score|applied_at|id)` for job candidates
- **Serving:** Nginx (`/api/*` → backend:8000, `/*` → frontend:3000) in Docker Compose; Vite proxy for local dev; CORS for Render
- **Deployment:** Render + Cloudflare R2; MinIO locally only
- **Migrations:** 4 files done — `0001` trigger function, `0002` full schema (owns enum types), `0003` attach triggers, `0004` strengths/gaps/ai_status
- **Frontend markdown:** `fit_explanation` and `ai_parsed_resume.summary` rendered via `react-markdown` (default plugins — no rehype-raw)
- **Optimistic updates:** Pipeline status selector reverts to previous value + shows error toast on PATCH failure
- **Token storage:** httpOnly cookies only — no localStorage or sessionStorage
- **Tag input:** Enter/comma commits a tag; Backspace removes last; duplicates silently dropped; max 30
- **CandidateWithApplicationResponse shape:** nested `application: ApplicationInCandidateList` (not flat); no `application_summaries` on list items (detail page gets that from `GET /candidates/:id`)

## Next Action

**WI-006 — Frontend scaffold**
Files: `frontend/src/`, `tailwind.config.js`, `postcss.config.js`, `src/index.css`, `src/main.tsx`, `src/api/client.ts`, `src/contexts/AuthContext.tsx`, `src/components/ProtectedLayout.tsx`
- Tailwind CSS configured
- React Router skeleton with routes for all pages
- Axios client with cookie auth + 401 interceptor
- AuthContext with session restore on mount

After WI-006: **WI-007** (Login + Register pages) and **WI-008** (Jobs list page) can proceed.

Full work item specs: `docs/planning/prds/gappeo-frontend-breakdown.md`
