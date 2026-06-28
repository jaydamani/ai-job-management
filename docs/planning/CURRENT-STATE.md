# Current State — Gappeo

**Last updated:** 2026-06-28
**Branch:** master
**Overall status:** Backend complete (31/31 tests passing); Frontend complete — candidate navigation fixed, add-candidate atomic flow fixed; ready for end-to-end smoke test

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
| Auth (JWT + cookies) | ✅ Complete | httpOnly cookie auth; access_token 15min, refresh_token 30d; server-side revocation |
| Jobs (CRUD + filter) | ✅ Complete | 7 query filters, cursor pagination, GIN trgm index on title |
| Candidates (CRUD + AI + pipeline) | ✅ Complete | PDF upload, multimodal AI parse/score, fit_score cursor; strengths/gaps/ai_status; nested response; rescore endpoint |
| Alembic migrations | ✅ Complete | 3 migrations: 0001 trigger fn, 0002 full schema (with strengths/gaps/ai_status + resume_s3_key on applications), 0003 attach triggers |
| Docker / Infra | ✅ Complete | docker-compose, nginx, Dockerfile, .env.example |
| AI service | ✅ Complete | OpenRouter + structured output (json_schema) + multimodal PDF via pymupdf; FIT_SCHEMA returns strengths[] + gaps[] |
| Backend API contract | ✅ Complete | All schemas finalized; `POST /candidates` accepts `job_id?` and returns `CandidateDetailResponse` |
| Backend tests | ✅ Complete | 31/31 passing; cookie auth; no DB dependency; covers auth, jobs, candidates, applications, status update, rescore |
| WI-006: Frontend scaffold | ✅ Complete | Tailwind, routing, Axios client + 401 interceptor, AuthContext, ProtectedLayout, Navbar |
| WI-007: Login + Register pages | ✅ Complete | RHF + Zod; htmlFor/id accessibility fixes applied |
| WI-008: Jobs list page | ✅ Complete | Card click → candidates list; Edit as secondary action; infinite scroll, 7 filters |
| WI-009: Job form page | ✅ Complete | Create/edit/close; "View Candidates" button in edit-mode header; tag input for required_skills |
| WI-010: Candidates list page | ✅ Complete | Infinite scroll, fit score badges, job header |
| WI-011: Add Candidate page | ✅ Complete | Two-step flow; single atomic POST creates candidate + application; redirect to candidate detail |
| WI-012: Candidate Detail page | ✅ Complete | Pipeline selector (optimistic + rollback), resume section, AI panel, parsed resume accordion |
| WI-014: Frontend smoke tests | ✅ Complete | MSW + Vitest; 8/8 passing |
| WI-015: README.md | ✅ Complete | Written to project root |
| Frontend dep upgrade | ✅ Complete | All deps to latest majors (React 19, Router 7, Tailwind 4, TS 6, Vite 8, Zod 4); Tailwind v4 config migrated; build clean |

## Schema Status (canonical)

| Table | Key columns |
|-------|-------------|
| `recruiters` | id, email, password_hash, name, created_at, updated_at |
| `refresh_tokens` | id, recruiter_id, token_hash, expires_at, revoked |
| `jobs` | id, recruiter_id, title, description, department, location, salary_min/max, required_skills[], employment_type, experience_level, remote_type, status |
| `candidates` | id, recruiter_id, name, email, phone, location_preference, linkedin_url, portfolio_url, github_url, expected_salary_min/max, notice_period_days, earliest_joining_date, source, referred_by, notes |
| `candidate_job_applications` | id, candidate_id, job_id, status, fit_score, fit_explanation, ai_parsed_resume (JSONB), strengths (JSONB), gaps (JSONB), ai_status, resume_s3_key, interview_notes, applied_at |

## Known Gap

When resume parse fails (before scoring), `ai_status` is not persisted to DB — stays null. Response correctly returns `"failed"`. Fix deferred (low priority — rescore handles recovery).

## Key Architecture Decisions (locked)

- **Auth:** JWT 15-min access + 30-day refresh; refresh stored as bcrypt hash in `refresh_tokens`; tokens in httpOnly cookies (`access_token`, `refresh_token`); no tokens in response body or localStorage
- **Candidate–Job:** Many-to-many via `CandidateJobApplication`; `UNIQUE(candidate_id, job_id)`
- **Resume:** Per-application — `resume_s3_key` lives on `candidate_job_applications`, not `candidates`
- **Pipeline:** applied → screened → interviewed → rejected / hired
- **AI:** LiteLLM → OpenRouter; default `openrouter/anthropic/claude-sonnet-4-5`; multimodal PDF via pymupdf (pages → PNG images → `image_url` blocks); structured output via `json_schema` response format (strict); parse + score are separate calls; score 0–100 stored per application; `ai_status` values: `"complete"` / `"failed"`; `FIT_SCHEMA` returns `strengths[]` + `gaps[]`
- **AI retry:** `POST /candidates/:id/applications/:appId/rescore` — no body; backend re-runs scoring on the stored S3 PDF
- **Upload:** PDF only, 5 MB, python-magic MIME validation; boto3/S3 throughout; presigned URLs via `get_presigned_url` (1-hour expiry); `resume_url` (presigned) exposed on application-level response schemas
- **Pagination:** Cursor-based, 20/fetch; `base64(created_at|id)` for jobs/candidates; `base64(fit_score|applied_at|id)` for job candidates
- **Serving:** Nginx (`/api/*` → backend:8000, `/*` → frontend:3000) in Docker Compose; Vite proxy for local dev; CORS for Render
- **Deployment:** Render + Cloudflare R2; MinIO locally only
- **Migrations:** 0001 trigger function, 0002 full schema (owns all enum types + all columns), 0003 attach triggers
- **Frontend markdown:** `fit_explanation` and `ai_parsed_resume.summary` rendered via `react-markdown`
- **Optimistic updates:** Pipeline status selector reverts to previous value + shows error toast on PATCH failure
- **Token storage:** httpOnly cookies only — no localStorage or sessionStorage
- **Tag input:** Enter/comma commits a tag; Backspace removes last; duplicates silently dropped; max 30
- **CandidateWithApplicationResponse shape:** nested `application: ApplicationInCandidateList`; `resume_url` is on the nested application object
- **TypeScript types restriction:** `"types": ["vite/client", "vitest/globals"]` in tsconfig.json prevents transitive @types auto-discovery
- **POST /candidates:** accepts optional `job_id`; atomically creates candidate + application in single transaction; returns `CandidateDetailResponse` (includes `applications` list)
- **Job card UX:** primary click → candidates list; footer has "View Candidates" (primary) and "Edit" (secondary)

## Next Action

**Commit this session's fixes, then end-to-end smoke test with `docker-compose up`**

```bash
git add backend/app/api/candidates.py backend/app/schemas/candidate.py backend/app/services/candidate_service.py \
        frontend/src/api/candidates.ts frontend/src/pages/AddCandidatePage.tsx \
        frontend/src/pages/JobFormPage.tsx frontend/src/pages/JobsPage.tsx \
        frontend/src/types/index.ts
git commit -m "fix: candidate navigation and add-candidate atomic flow"
```

Smoke test flow:
1. `cp .env.example .env` — fill in `JWT_SECRET`, `ANTHROPIC_API_KEY`, `AI_MODEL`
2. `docker-compose up`
3. Register → create job → add candidate with PDF → verify redirect to candidate detail → change pipeline status
