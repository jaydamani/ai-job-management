# Gappeo — Recruiter Management System

## Project Overview

A full-stack recruiter management system where recruiters can manage job openings and candidates, with AI-powered resume parsing and fit scoring.

**Stack:** FastAPI · PostgreSQL · React · TypeScript · JWT Auth · Docker Compose

## Modules

| Module | Description |
|--------|-------------|
| **Auth** | Recruiter register/login with JWT. All routes protected. |
| **Jobs** | Create, edit, close job openings. List and filter. |
| **Candidates** | CRUD candidates linked to jobs. Resume upload + AI parsing + fit scoring. |
| **Frontend** | React/TypeScript UI: login screen + job/candidate management views. |
| **Docker** | Single `docker-compose up` starts backend, frontend, and database. |

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
├── docker-compose.yml
├── .env.example
└── README.md
```

## Key Decisions & Architecture Notes

- **Auth:** JWT tokens via `python-jose`; refresh token strategy TBD
- **AI Layer:** TBD
- **File uploads:** Resumes stored locally (volume mount in Docker) or S3-compatible
- **Database:** PostgreSQL via SQLAlchemy ORM + Alembic for migrations
- **Frontend state:** React Query for server state; minimal local state

## Environment Variables

See `.env.example` for required keys:
- `DATABASE_URL` — PostgreSQL connection string
- `JWT_SECRET` — Secret for signing JWTs
- `ANTHROPIC_API_KEY` — Claude API key for AI features
