# Gappeo — Recruiter Management System

## Project Overview

A full-stack recruiter management system where recruiters can manage job openings and candidates, with AI-powered resume parsing and fit scoring.

**Stack:** FastAPI · PostgreSQL · MinIO · React · TypeScript · JWT Auth · Nginx · Docker Compose

## Modules

| Module | Description |
|--------|-------------|
| **Auth** | Recruiter register/login with JWT. All routes protected. |
| **Jobs** | Create, edit, close job openings. List and filter. |
| **Candidates** | CRUD candidates linked to jobs. Resume upload + AI parsing + fit scoring. |
| **Frontend** | React/TypeScript UI: login screen + job/candidate management views. |
| **Docker** | Single `docker-compose up` starts backend, frontend, Nginx proxy, Postgres, and MinIO. |

## Development Commands

```bash
# Start all services
docker-compose up

# Backend only (local dev)
cd backend && uvicorn app.main:app --reload

# Frontend only (local dev)
cd frontend && npm run dev
```

## Project Structure (target)

```
gappeo/
├── backend/           # FastAPI app
│   ├── app/
│   │   ├── api/       # Route handlers
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   └── main.py
│   ├── alembic/       # DB migrations
│   └── Dockerfile
├── frontend/          # React + TypeScript
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/
│   │   └── main.tsx
│   └── Dockerfile
├── nginx/
│   └── nginx.conf         # Reverse proxy: /api → backend, / → frontend
├── docker-compose.yml
├── .env.example
└── README.md
```

## Key Decisions & Architecture Notes

- **Auth:** JWT tokens via `python-jose`; 15-min access + refresh token; server-side revocation via `refresh_tokens` DB table (token stored as bcrypt hash)
- **AI Layer:** LiteLLM for provider-agnostic completions — swap models via `AI_MODEL` env var (e.g. `claude-sonnet-4-6`, `gpt-4o`); default `claude-sonnet-4-6`; **multimodal** — PDF bytes sent directly as a base64 `document` content block (no text extraction step); eliminates image-only PDF failures; Claude-native feature, falls back to text extraction for non-Claude providers
- **File uploads:** PDF resumes stored in MinIO (S3-compatible); local MinIO container in docker-compose, production points to managed S3 via env vars
- **Database:** PostgreSQL via SQLAlchemy ORM + Alembic migrations; local Postgres in docker-compose, production points to managed DB via env vars
- **Serving:** Nginx reverse proxy — `/api/*` → FastAPI (8000), `/*` → React (3000); single origin for both services
- **Frontend state:** React Query for server state; minimal local state

## Environment Variables

See `.env.example` for required keys:
- `DATABASE_URL` — PostgreSQL connection string
- `JWT_SECRET` — Secret for signing JWTs
- `AI_MODEL` — LiteLLM model string, e.g. `claude-sonnet-4-6`, `gpt-4o` (default: `claude-sonnet-4-6`)
- `ANTHROPIC_API_KEY` — Required when using Claude models
- `OPENAI_API_KEY` — Required when using OpenAI models
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — S3 credentials (use MinIO values locally)
- `S3_BUCKET` — Bucket name for resume uploads
- `S3_ENDPOINT_URL` — Override S3 endpoint (set to `http://minio:9000` locally; omit in production to hit real AWS)
