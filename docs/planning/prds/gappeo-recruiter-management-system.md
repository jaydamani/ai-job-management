---
title: "Gappeo — Recruiter Management System"
slug: gappeo-recruiter-management-system
source: file://Gappeo_Assignment.md
initiative_id: null
imported_at: "2026-06-22T00:00:00Z"
status: validated
validation_report: docs/planning/prds/gappeo-recruiter-management-system-validation.md
validation_score: 81
author: unknown
version: "1.1"
---

# Gappeo — Recruiter Management System PRD

## Problem Statement

Recruiters need a centralized tool to manage job openings and evaluate candidates efficiently. The manual process of tracking applicants across spreadsheets and email is slow and error-prone. An AI-powered system can dramatically reduce time-to-screen by automatically parsing resumes and scoring candidate fit against job requirements.

## Target Users

- **Primary:** Recruiters (internal HR or agency-based) who manage multiple open positions and large candidate pools.
- **Note:** Each recruiter account is isolated — a recruiter can only access jobs and candidates they created.

## Data Model

### Job

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | System | Primary key |
| recruiter_id | UUID | System | FK to Recruiter — enforces ownership isolation |
| title | string | Yes | Job title |
| description | text | Yes | Full role description |
| department | string | No | Department name |
| location | string | No | Office location or "Remote" |
| salary_min | integer | No | Minimum salary (currency units) |
| salary_max | integer | No | Maximum salary (currency units) |
| required_skills | string[] | No | List of required skills — used for AI fit scoring |
| employment_type | enum | No | `full_time` \| `part_time` \| `contract` \| `internship` |
| experience_level | enum | No | `junior` \| `mid` \| `senior` \| `lead` |
| remote_type | enum | No | `onsite` \| `hybrid` \| `remote` |
| status | enum | System | `open` \| `closed` — defaults to `open` |
| created_at | timestamp | System | Auto-set |
| updated_at | timestamp | System | Auto-set |

### Candidate

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | System | Primary key |
| recruiter_id | UUID | System | FK to Recruiter — enforces ownership isolation |
| name | string | Yes | Full name |
| email | string | Yes | Contact email |
| phone | string | No | Phone number |
| location_preference | string | No | Preferred work location |
| linkedin_url | string | No | LinkedIn profile URL |
| portfolio_url | string | No | Portfolio website URL |
| github_url | string | No | GitHub profile URL |
| expected_salary_min | integer | No | Expected salary range min |
| expected_salary_max | integer | No | Expected salary range max |
| notice_period_days | integer | No | Notice period in days |
| earliest_joining_date | date | No | Earliest available start date |
| source | string | No | How the candidate was sourced (e.g., LinkedIn, referral, job board) |
| referred_by | string | No | Name of referrer, if applicable |
| notes | text | No | Recruiter free-text notes |
| resume_path | string | No | Server-side path to uploaded resume file |
| created_at | timestamp | System | Auto-set |
| updated_at | timestamp | System | Auto-set |

### CandidateJobApplication (join table — many-to-many)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | System | Primary key |
| candidate_id | UUID | Yes | FK to Candidate |
| job_id | UUID | Yes | FK to Job |
| status | enum | Yes | `applied` \| `screened` \| `interviewed` \| `rejected` \| `hired` — defaults to `applied` |
| fit_score | integer | No | 0–100 AI-generated fit score |
| fit_explanation | text | No | AI-generated explanation of the score |
| ai_parsed_resume | jsonb | No | Structured data extracted by AI from the resume (includes current_title, current_company) |
| interview_notes | text | No | Recruiter notes added when status reaches `interviewed` |
| applied_at | timestamp | System | Auto-set |
| updated_at | timestamp | System | Auto-set |

### Recruiter

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| id | UUID | System | Primary key |
| email | string | Yes | Unique — used for login |
| password_hash | string | System | bcrypt hash — never returned in API responses |
| name | string | No | Display name |
| created_at | timestamp | System | Auto-set |

## Requirements

### Module 1 — Auth

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTH-1 | Recruiter can register with email (unique), password (min 8 chars), and optional name | MUST |
| AUTH-2 | Recruiter can log in and receive a short-lived access token (15 min) and a refresh token | MUST |
| AUTH-3 | All job and candidate routes require a valid access token — 401 if missing or expired | MUST |
| AUTH-4 | Recruiter can use a valid refresh token to obtain a new access token | MUST |
| AUTH-5 | Recruiter can log out — refresh token is invalidated server-side | MUST |
| AUTH-6 | Passwords are hashed with bcrypt before storage — plaintext never stored | MUST |

### Module 2 — Jobs

| ID | Requirement | Priority |
|----|-------------|----------|
| JOB-1 | Recruiter can create a job opening (title, description required; department, location, salary range, required_skills optional) | MUST |
| JOB-2 | Recruiter can edit any field of a job they own | MUST |
| JOB-3 | Recruiter can close a job opening (status → `closed`) | MUST |
| JOB-4 | Recruiter can list their own job openings with infinite scroll (cursor-based, 20 items per fetch) | MUST |
| JOB-5 | Jobs list supports filtering by: status, title (partial match), department, location, employment_type, experience_level, remote_type | MUST |
| JOB-6 | A recruiter cannot view, edit, or close jobs owned by another recruiter — 404 returned | MUST |

### Module 3 — Candidates

| ID | Requirement | Priority |
|----|-------------|----------|
| CAND-1 | Recruiter can add a candidate record (name, email required; all other fields optional) | MUST |
| CAND-2 | Recruiter can link a candidate to one or more jobs (creates a CandidateJobApplication record) | MUST |
| CAND-3 | Recruiter can view a candidate and their applications across jobs | MUST |
| CAND-4 | Recruiter can update any candidate field | MUST |
| CAND-5 | Recruiter can remove a candidate (and all their applications) | MUST |
| CAND-6 | Recruiter can upload a PDF resume (≤ 5 MB) for a candidate | MUST |
| CAND-7 | Server validates file MIME type as `application/pdf` server-side — rejects non-PDF with 400 | MUST |
| CAND-8 | On resume upload, system calls AI API to extract structured data and stores it in `ai_parsed_resume` on the application | MUST |
| CAND-9 | On resume upload, system calls AI API to score fit (0–100) and generate explanation against the job's `description` and `required_skills`, stored on the application | MUST |
| CAND-10 | If the AI API is unavailable or returns an error, resume is saved but `fit_score` and `ai_parsed_resume` are null; a retriable error is returned to the client | MUST |
| CAND-11 | Recruiter can update a candidate application's pipeline status (`applied` → `screened` → `interviewed` → `rejected`/`hired`) | MUST |
| CAND-12 | Recruiter can list candidates for a job, sorted by fit_score desc, with infinite scroll (cursor-based, 20 items per fetch) | MUST |
| CAND-13 | A recruiter cannot view, edit, or remove candidates owned by another recruiter — 404 returned | MUST |
| CAND-14 | Bulk resume upload — upload multiple PDFs at once; system parses and scores each; response includes all candidates ranked by fit_score desc | BONUS |

### Module 4 — Frontend

| ID | Requirement | Priority |
|----|-------------|----------|
| FE-1 | Login and registration screens | MUST |
| FE-2 | Jobs list view with filters (status, title, department, location) and infinite scroll | MUST |
| FE-3 | Job detail / create / edit form | MUST |
| FE-4 | Candidates list for a job, sorted by fit score, with infinite scroll | MUST |
| FE-5 | Candidate detail view: contact info, pipeline stage selector, resume link, AI-parsed data, fit score + explanation | MUST |
| FE-6 | Add / edit candidate form | MUST |
| FE-7 | Resume upload UI with loading state (AI scoring takes time) and error handling if AI is unavailable | MUST |
| FE-8 | Bulk resume upload UI with ranked results display | BONUS |

### Module 5 — Docker

| ID | Requirement | Priority |
|----|-------------|----------|
| DOCK-1 | Entire app (backend + frontend + database) runs with `docker-compose up` | MUST |
| DOCK-2 | No manual setup required beyond creating a `.env` file from `.env.example` | MUST |
| DOCK-3 | Resume upload volume is mounted persistently so files survive container restarts | MUST |

### Deployment

| ID | Requirement | Priority |
|----|-------------|----------|
| DEPLOY-1 | Full app deployed on a free-tier cloud platform (implementer's choice) | MUST |
| DEPLOY-2 | Backend API and frontend both publicly accessible | MUST |
| DEPLOY-3 | Live URL shared with submission | MUST |

### Documentation

| ID | Requirement | Priority |
|----|-------------|----------|
| DOC-1 | README with local setup steps | MUST |
| DOC-2 | `.env.example` with all required env var keys and descriptions | MUST |
| DOC-3 | README section: "What I'd improve with more time" | BONUS |
| DOC-4 | GitHub repo (public) with clean commit history | MUST |

## AI Output Contract

**Resume parsing (CAND-8):** The AI must return a structured JSON object with at minimum:
```json
{
  "name": "string",
  "email": "string",
  "phone": "string",
  "current_title": "string",
  "current_company": "string",
  "summary": "string",
  "skills": ["string"],
  "experience": [{"title": "string", "company": "string", "duration": "string", "description": "string"}],
  "education": [{"degree": "string", "institution": "string", "year": "string"}],
  "total_experience_years": "number"
}
```

**Fit scoring (CAND-9):** The AI must return:
```json
{
  "score": 0-100,
  "explanation": "string (2–4 sentences explaining the score)",
  "strengths": ["string"],
  "gaps": ["string"]
}
```

## Acceptance Criteria

- A recruiter can register, log in, and all subsequent actions require a valid JWT (401 on missing/expired token).
- A recruiter can only access their own jobs and candidates — accessing another recruiter's data returns 404.
- A recruiter can create/edit/close jobs; the jobs list filters by status, title, department, and location.
- A recruiter can upload a PDF resume ≤ 5 MB; the system validates MIME type server-side and returns 400 for non-PDF.
- On successful upload, the system calls the AI API and populates `fit_score`, `fit_explanation`, and `ai_parsed_resume` on the application.
- If the AI API fails, the resume saves and a retriable error is returned — the recruiter can retry scoring.
- Candidate applications have a pipeline status the recruiter can advance.
- The entire stack starts with `docker-compose up` plus a `.env` file — no other manual steps.
- A public live URL is accessible for both backend and frontend.

## Constraints

- **Stack is fixed:** FastAPI · PostgreSQL · React · TypeScript · JWT Auth · Docker Compose
- **AI API:** Claude API (`claude-sonnet-4-6`) for resume parsing and fit scoring
- **File uploads:** PDF only, 5 MB max, server-side MIME validation; stored in a Docker volume
- **Pagination:** Infinite scroll / cursor-based pagination, 20 items per fetch
- **Auth:** 15-minute access tokens + refresh tokens; bcrypt password hashing; server-side refresh token invalidation on logout
- **Authorization:** Per-recruiter data isolation — each recruiter sees only their own records
- **Candidate–Job:** Many-to-many via CandidateJobApplication join table
- **Pipeline stages:** `applied` → `screened` → `interviewed` → `rejected` / `hired`
- **Free-tier deployment:** Sleeping on inactivity is acceptable with a note in README
