# Session Plan — 2026-06-23

**Date:** 2026-06-23 | **Branch:** master | **Focus:** feature

## Previous Session
- Last: 2026-06-23 — general
- Completed: Architecture decisions locked; CLAUDE.md, CURRENT-STATE.md, PRD all consistent; LiteLLM multimodal approach; Render + Cloudflare R2 deployment; CORS/serving strategy finalized; enrichment doc complete (score: 81)
- Carried over: All implementation modules (none started)

## Active Issues (local state — no task management integration)

| Priority | Task | Status |
|----------|------|--------|
| P0 | Backend scaffold: FastAPI + SQLAlchemy + Alembic + project structure | Not started |
| P1 | Module 1 — Auth: register/login, JWT 15min + refresh token, bcrypt, server-side revocation | Not started |
| P2 | Module 2 — Jobs: CRUD + filter (status, title, dept, location, emp_type, exp_level, remote_type) | Not started |
| P3 | Module 3 — Candidates: CRUD + PDF upload + AI parsing/scoring + pipeline status | Not started |
| P4 | Module 4 — Frontend: React/TypeScript UI | Not started |
| P5 | Module 5 — Docker: docker-compose + Dockerfiles + Nginx | Not started |
| P6 | .env.example + README | Not started |

## Recommended First Task

**Backend scaffold** — create FastAPI project structure, install dependencies, configure SQLAlchemy + Alembic, and run the 4 migration files from the enrichment report (Section 01 DDL + Section 04 migration strategy).

## Working Tree

Clean — no uncommitted changes.

## Key Architecture Reminders

- AI: LiteLLM, default `claude-sonnet-4-6`, multimodal PDF via base64 document block
- Auth: JWT 15min access + 30-day refresh stored hashed in `refresh_tokens` table
- Storage: MinIO locally → Cloudflare R2 in prod (S3-compatible, same boto3 code)
- Serving: Nginx (Docker Compose) / Vite proxy (local) / CORS (Render)
