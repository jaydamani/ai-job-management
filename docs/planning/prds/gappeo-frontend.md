---
title: "Gappeo — Frontend"
slug: gappeo-frontend
source: file://Gappeo_Assignment.md + file://docs/planning/prds/gappeo-recruiter-management-system.md
parent_prd: gappeo-recruiter-management-system
imported_at: "2026-06-25T00:00:00Z"
status: enriched
validation_report: docs/planning/prds/gappeo-frontend-validation.md
validation_score: 93
validated_at: "2026-06-28T00:00:00Z"
enrichment_report: docs/planning/prds/gappeo-frontend-enrichment.md
enriched_at: "2026-06-28T00:00:00Z"
breakdown_report: docs/planning/prds/gappeo-frontend-breakdown.md
breakdown_at: "2026-06-28T00:00:00Z"
author: unknown
version: "1.0"
---

# Gappeo — Frontend PRD

## Problem Statement

Recruiters need a clean, fast UI to manage job openings and candidates without context-switching between tools. The frontend is the primary interface for the recruiter workflow: authenticate, post jobs, upload resumes, review AI scoring, and advance candidates through the pipeline.

## Target Users

- **Primary:** Recruiters (internal HR or agency-based) using the Gappeo system to manage their own job openings and candidate pools.

## Tech Stack

- **Framework:** React 18 + TypeScript (Vite)
- **Routing:** React Router v6
- **Server state:** TanStack Query (React Query) v5
- **Forms:** React Hook Form + Zod validation
- **HTTP client:** Axios with interceptor-based token refresh (`withCredentials: true` — cookie auth)
- **Styling:** Tailwind CSS (utility-first; no component library)
- **Markdown rendering:** `react-markdown` + `dompurify` (sanitized markdown for AI-generated text fields)

---

## Route Table

| Route | Page | Auth required |
|-------|------|---------------|
| `/login` | Login | No |
| `/register` | Register | No |
| `/jobs` | Jobs list (default redirect after login) | Yes |
| `/jobs/new` | Create job form | Yes |
| `/jobs/:jobId` | Job detail + edit + close | Yes |
| `/jobs/:jobId/candidates` | Candidates list for job | Yes |
| `/jobs/:jobId/candidates/new` | Add candidate to job | Yes |
| `/jobs/:jobId/candidates/:candidateId` | Candidate detail | Yes |

---

## API Client Contract

### Base URL

- **Local dev / Docker Compose:** relative (`/api`) — Nginx proxies to backend
- **Render deploy:** `VITE_API_URL` env var, baked in at build time

### Axios instance (`src/api/client.ts`)

Tokens are stored in **httpOnly cookies** (set by the backend). The frontend never reads or writes tokens — the browser sends them automatically on every request.

```typescript
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true,  // send cookies cross-origin
})

// No request interceptor needed — browser sends cookies automatically

// Response interceptor: on 401, attempt token refresh once via cookie
client.interceptors.response.use(
  r => r,
  async err => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        // POST /auth/refresh — no body; server reads refresh_token cookie
        await axios.post(
          `${import.meta.env.VITE_API_URL || '/api'}/auth/refresh`,
          {},
          { withCredentials: true }
        )
        return client(original)  // retry original request; new access_token cookie is set
      } catch {
        logout()  // refresh failed — clear auth state and redirect to /login
        return Promise.reject(err)
      }
    }
    return Promise.reject(err)
  }
)
```

> **Note:** The interceptor does NOT retry multipart/form-data requests on 401 (resume upload). If a resume upload returns 401 after a failed refresh, the user is redirected to `/login`. Resume uploads are short-lived operations and token expiry mid-upload is extremely unlikely (15-min access token).

### API modules

| Module | File |
|--------|------|
| Auth | `src/api/auth.ts` |
| Jobs | `src/api/jobs.ts` |
| Candidates | `src/api/candidates.ts` |

---

## API Endpoints Used

### Auth

| Method | Path | Request | Response |
|--------|------|---------|----------|
| POST | `/auth/register` | `{ email, password, name? }` | `RecruiterResponse` (sets `access_token` + `refresh_token` httpOnly cookies) |
| POST | `/auth/login` | `{ email, password }` | `RecruiterResponse` (sets `access_token` + `refresh_token` httpOnly cookies) |
| POST | `/auth/refresh` | — (reads `refresh_token` cookie) | `204` (rotates `access_token` cookie) |
| POST | `/auth/logout` | — (reads `refresh_token` cookie) | `204` (clears both cookies) |

### Jobs

| Method | Path | Query / Body | Response |
|--------|------|-------------|----------|
| GET | `/jobs` | `?cursor&status&title&department&location&employment_type&experience_level&remote_type` | `{ items: Job[], next_cursor }` |
| POST | `/jobs` | JobCreate body | `Job` |
| GET | `/jobs/:id` | — | `Job` |
| PUT | `/jobs/:id` | JobUpdate body | `Job` |
| PATCH | `/jobs/:id/close` | — | `Job` |

### Candidates

| Method | Path | Query / Body | Response |
|--------|------|-------------|----------|
| GET | `/jobs/:jobId/candidates` | `?cursor` | `{ items: CandidateWithApplication[], next_cursor }` — sorted fit_score desc |
| POST | `/candidates` | CandidateCreate body | `Candidate` |
| GET | `/candidates/:id` | — | `CandidateWithApplications` |
| PUT | `/candidates/:id` | CandidateUpdate body | `Candidate` |
| DELETE | `/candidates/:id` | — | `204` |
| POST | `/candidates/:id/applications` | `{ job_id }` | `Application` |
| PATCH | `/candidates/:id/applications/:appId/status` | `{ status }` | `Application` |
| POST | `/candidates/:id/applications/:appId/resume` | `multipart/form-data` `file=<pdf>` | `{ resume_url, ai_status, fit_score?, fit_explanation?, strengths?, gaps?, ai_parsed_resume? }` |
| POST | `/candidates/:id/applications/:appId/rescore` | — | `{ ai_status, fit_score?, fit_explanation?, strengths?, gaps?, ai_parsed_resume? }` |

### Key Response Types

```typescript
// Job
interface Job {
  id: string
  title: string
  description: string
  department?: string
  location?: string
  salary_min?: number
  salary_max?: number
  required_skills: string[]
  employment_type?: 'full_time' | 'part_time' | 'contract' | 'internship'
  experience_level?: 'junior' | 'mid' | 'senior' | 'lead'
  remote_type?: 'onsite' | 'hybrid' | 'remote'
  status: 'open' | 'closed'
  candidate_count: number
  created_at: string
}

// Candidate (in job candidates list)
interface CandidateWithApplication {
  id: string
  name: string
  email: string
  phone?: string
  location_preference?: string
  linkedin_url?: string
  portfolio_url?: string
  github_url?: string
  resume_url?: string          // presigned S3 URL
  created_at: string
  application: {
    id: string
    job_id: string
    job_title: string
    status: PipelineStatus
    fit_score?: number
    fit_explanation?: string
    strengths?: string[]
    gaps?: string[]
    ai_parsed_resume?: ParsedResume
    ai_status?: 'complete' | 'failed'
    applied_at: string
  }
}

// Candidate (detail view)
interface CandidateWithApplications {
  id: string
  name: string
  email: string
  phone?: string
  location_preference?: string
  linkedin_url?: string
  portfolio_url?: string
  github_url?: string
  resume_url?: string          // presigned S3 URL
  created_at: string
  applications: {
    id: string
    job_id: string
    job_title: string
    status: PipelineStatus
    fit_score?: number
    fit_explanation?: string
    strengths?: string[]
    gaps?: string[]
    ai_parsed_resume?: ParsedResume
    ai_status?: 'complete' | 'failed'
    applied_at: string
  }[]
}

type PipelineStatus = 'applied' | 'screened' | 'interviewed' | 'rejected' | 'hired'

interface ParsedResume {
  name: string
  email: string
  phone: string
  current_title: string
  current_company: string
  summary: string
  skills: string[]
  experience: { title: string; company: string; duration: string; description: string }[]
  education: { degree: string; institution: string; year: string }[]
  total_experience_years: number
}

interface ApplicationSummary {
  job_id: string
  job_title: string
  status: PipelineStatus
  fit_score?: number
}
```

---

## Component Tree

```
App
├── AuthProvider (context: recruiter, tokens, login/logout)
├── Routes
│   ├── /login → LoginPage
│   │   └── LoginForm (email, password; RHF + Zod)
│   ├── /register → RegisterPage
│   │   └── RegisterForm (email, password, name; RHF + Zod)
│   └── ProtectedLayout (redirect to /login if no token)
│       ├── Navbar (logo, "Jobs" link, logout button)
│       ├── /jobs → JobsPage
│       │   ├── JobFilters (status, title search, dept, location, emp_type, exp_level, remote_type)
│       │   ├── JobList (infinite scroll — useInfiniteQuery)
│       │   │   └── JobCard (title, dept, location, status badge, candidate_count)
│       │   └── "+ New Job" button → /jobs/new
│       ├── /jobs/new → JobFormPage (create mode)
│       │   └── JobForm (all fields; RHF + Zod)
│       ├── /jobs/:jobId → JobDetailPage
│       │   ├── JobForm (edit mode, pre-filled)
│       │   ├── "Close Job" button (PATCH /jobs/:id/close)
│       │   └── "View Candidates" link → /jobs/:jobId/candidates
│       ├── /jobs/:jobId/candidates → CandidatesPage
│       │   ├── CandidateList (infinite scroll — useInfiniteQuery; sorted by fit_score desc)
│       │   │   └── CandidateCard (name, email, fit_score badge, pipeline status, current_title)
│       │   └── "+ Add Candidate" button → /jobs/:jobId/candidates/new
│       └── /jobs/:jobId/candidates/:candidateId → CandidateDetailPage
│           ├── CandidateInfo (contact, links, expected salary)
│           ├── PipelineSelector (status dropdown: applied → screened → interviewed → rejected/hired)
│           ├── ResumeUpload (file input, upload button, progress indicator, retry on AI fail)
│           ├── AIPanel (fit_score gauge, fit_explanation, strengths/gaps, parsed resume accordion)
│           └── ApplicationSummaries (list of other jobs this candidate applied to)
```

---

## Page Specifications

### LoginPage / RegisterPage

- Simple centered card layout
- On success: cookies are set by the server; call `login(recruiterResponse)` to store recruiter data in `AuthContext`; redirect to `/jobs`
- On error: display inline error message (invalid credentials, email taken, etc.)
- Link between login ↔ register pages

### JobsPage

- **Filters bar:** status select (all / open / closed), title text search (debounced 300ms), department text, location text, employment_type select, experience_level select, remote_type select
- **Infinite scroll:** `useInfiniteQuery` + IntersectionObserver sentinel div at list bottom
- **JobCard:** title (bold), department, location, status badge (green=open, gray=closed), `{candidate_count} candidates` counter, created date
- Click card → `/jobs/:jobId`

### JobFormPage (create + edit)

- **Fields:** title*, description* (textarea), department, location, salary_min, salary_max, required_skills (tag input — comma-separated, stored as string[]), employment_type select, experience_level select, remote_type select, status (edit mode only)
- **Tag input behavior:** pressing Enter or comma commits the current input as a tag; Backspace on empty input removes the last tag; duplicates are silently dropped; no maximum tag count
- `*` = required, validated by Zod
- Create: POST `/jobs` → redirect to `/jobs/:newId`
- Edit: PUT `/jobs/:jobId` → stay on page, show success toast
- "Close Job" button visible in edit mode: PATCH `/jobs/:jobId/close` → update status in UI

### CandidatesPage

- Breadcrumb: `Jobs > {job title} > Candidates`
- Job summary header (title, status, dept/location, salary range, required skills chips)
- Candidate list sorted by fit_score desc; `fit_score` shown as colored badge (green ≥ 70, yellow 40–69, red < 40, gray = not scored)
- Status badge per pipeline stage
- `current_title` / `current_company` from `ai_parsed_resume` if available
- "+ Add Candidate" button

### AddCandidatePage (`/jobs/:jobId/candidates/new`)

**Two-step flow:**

**Step 1 — Resume upload (optional but recommended):**
- PDF file input (≤ 5 MB)
- If skipped → go to Step 2 with blank form

**Step 2 — Candidate form:**
- Fields: name*, email*, phone, location_preference, linkedin_url, portfolio_url, github_url, expected_salary_min, expected_salary_max, notice_period_days, source, notes
- On submit:
  1. POST `/candidates` with form data
  2. POST `/candidates/:id/applications` with `{ job_id }`
  3. If resume was selected in Step 1: POST `.../applications/:appId/resume` (multipart)
     - Show spinner with "Parsing resume with AI…" text
     - If `ai_status === 'failed'`: show warning toast "AI scoring unavailable — you can retry from the candidate detail page"
  4. On success: redirect to `/jobs/:jobId/candidates/:candidateId`

### CandidateDetailPage

- **Header:** name, email, phone, location_preference, linkedin/portfolio/github icon links
- **Pipeline selector:** `<select>` bound to current status; on change → PATCH status endpoint → optimistic update
- **Resume section:**
  - If `resume_url` exists: "View Resume" link (opens presigned S3 URL in new tab) + "Re-upload Resume" button
  - If no resume: "Upload Resume" button
  - Upload flow: file input → POST multipart → spinner → on success refresh candidate data
  - If `ai_status === 'failed'`: "AI scoring failed — retry" button that POSTs to `POST /candidates/:id/applications/:appId/rescore` (no body; backend re-runs scoring on the already-stored S3 PDF); no re-upload required
- **AI Panel** (shown if `fit_score` or `ai_parsed_resume` exists):
  - Fit score gauge / number (0–100) with color band
  - `fit_explanation` rendered as sanitized markdown (via `react-markdown` + `dompurify`)
  - Strengths list from `strengths[]` (green check icons) — shown if array is non-empty
  - Gaps list from `gaps[]` (orange warning icons) — shown if array is non-empty
  - Parsed resume accordion: Summary (sanitized markdown), Skills chips, Experience timeline, Education list, `total_experience_years`
- **Other applications:** list of `application_summaries` — job title, status badge, fit_score — each is a same-tab router link to `/jobs/:job_id/candidates/:candidateId`

---

## Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FE-1 | Login and registration screens with JWT storage and redirect | MUST |
| FE-2 | Jobs list with 7 filters (status, title, department, location, employment_type, experience_level, remote_type) and cursor infinite scroll | MUST |
| FE-3 | Job create form and edit form (same component, two modes); close job action | MUST |
| FE-4 | Candidates list for a job sorted by fit score, with infinite scroll and fit score color badges | MUST |
| FE-5 | Candidate detail: contact info, pipeline status selector, resume link/upload, AI panel (score + explanation + parsed data), other applications list | MUST |
| FE-6 | Add candidate form (name, email + optional fields) with application linking | MUST |
| FE-7 | Resume upload UI: file input, upload spinner "Parsing resume with AI…", success/failure handling, retry button on failure | MUST |
| FE-8 | Axios interceptor for transparent token refresh; logout on 401 after refresh failure | MUST |
| FE-9 | Responsive layout (desktop-first, usable on tablet); Tailwind CSS | MUST |
| FE-BONUS | Bulk resume upload UI: multi-file input, progress per file, ranked results table by fit_score desc | BONUS |

---

## Form Validation Rules (Zod)

### Job form

| Field | Rule |
|-------|------|
| `title` | required, string, min 1, max 200 |
| `description` | required, string, min 1 |
| `department` | optional, string, max 100 |
| `location` | optional, string, max 100 |
| `salary_min` | optional, positive integer |
| `salary_max` | optional, positive integer, ≥ salary_min if both present |
| `required_skills` | optional, string[], max 30 tags |
| `employment_type` | optional, enum: `full_time \| part_time \| contract \| internship` |
| `experience_level` | optional, enum: `junior \| mid \| senior \| lead` |
| `remote_type` | optional, enum: `onsite \| hybrid \| remote` |

### Candidate form

| Field | Rule |
|-------|------|
| `name` | required, string, min 1, max 200 |
| `email` | required, valid email format |
| `phone` | optional, string, max 30 |
| `location_preference` | optional, string, max 100 |
| `linkedin_url` | optional, valid URL |
| `portfolio_url` | optional, valid URL |
| `github_url` | optional, valid URL |
| `expected_salary_min` | optional, positive integer |
| `expected_salary_max` | optional, positive integer, ≥ expected_salary_min if both present |
| `notice_period_days` | optional, non-negative integer |
| `source` | optional, string, max 100 |
| `notes` | optional, string |

### Login / Register form

| Field | Rule |
|-------|------|
| `email` | required, valid email format |
| `password` | required, string, min 8 |
| `name` | optional (register only), string, max 200 |

---

## State Management

- **Auth state:** React context (`AuthContext`) — `{ recruiter, isAuthenticated, login, logout }`. No tokens in frontend state — cookies are httpOnly and managed by the browser. On app load, call `POST /auth/refresh` (no body) to restore session; if it fails, treat as unauthenticated. `login()` stores the returned `RecruiterResponse` in context. `logout()` calls `POST /auth/logout` (clears server-side cookie + refresh token DB row), then resets context.
- **Server state:** TanStack Query — all API data. Query keys: `['jobs', filters]`, `['job', jobId]`, `['candidates', jobId]`, `['candidate', candidateId]`.
- **Form state:** React Hook Form (local only, not in Query cache).
- **Toast notifications:** lightweight inline state (no library) — `{ message, type }` per page.

---

## Acceptance Criteria

- Unauthenticated routes redirect to `/login`; successful login redirects to `/jobs`
- Logout clears tokens and redirects to `/login`
- Jobs list filters update results without full page reload; infinite scroll loads next page when sentinel is visible
- Job form validates required fields (title, description) before submit; shows field-level errors
- Candidate list is sorted by fit_score descending; unscored candidates appear at the bottom
- Resume upload shows a spinner and "Parsing resume with AI…" message while the request is in-flight
- If AI scoring fails, the candidate is still created and a clear retry affordance is shown
- Pipeline status updates immediately (optimistic) and reflects server confirmation; if the PATCH request fails, the selector reverts to the previous value and an error toast is shown
- Presigned resume URL opens the PDF in a new browser tab
- All API errors surface a user-readable message (no raw JSON shown to the user)
- If resume upload fails during AddCandidatePage (after candidate + application already created), the user is redirected to `/jobs/:jobId/candidates/:candidateId` with a warning toast; the candidate is not lost and resume can be retried from the detail page
- Clicking a job link in "Other Applications" on CandidateDetailPage navigates in the same tab (standard SPA navigation) to `/jobs/:jobId/candidates/:candidateId`
- App runs with `docker-compose up` — Nginx serves frontend at `/`, proxies `/api/*` to backend

---

## Constraints

- No CSS component library (shadcn, MUI, Chakra) — Tailwind only
- No global state library (Redux, Zustand) — React Query + React context only
- PDF upload limit: 5 MB — validated client-side before sending
- Cursor pagination: `next_cursor` from response used as `cursor` query param for next page; `null` means end of list
- Access token: 15-minute expiry — refresh automatically via interceptor; do not show token expiry to user
- `VITE_API_URL`: empty string for local dev and Docker Compose (relative URLs); set to Render backend URL for Render static site
- Token storage: httpOnly cookies only — no `localStorage` or `sessionStorage` for tokens
- All links that open in a new tab (`target="_blank"`) must include `rel="noopener noreferrer"`
- AI-generated text fields (`fit_explanation`, `ai_parsed_resume.summary`) rendered via `react-markdown`; HTML output must be sanitized with `dompurify` before insertion
- Candidate-facing access is out of scope — the app is recruiter-only; presigned resume URLs are not access-controlled beyond what S3 provides

---

## Backend Changes Required

These changes must be made to the backend before implementing the corresponding frontend features.

### 1. Cookie-based Auth (replaces Authorization header + body token passing)

**`backend/app/api/auth.py`:**
- `POST /auth/login` — after successful auth, set two cookies on the response:
  - `access_token`: httpOnly, Secure (prod), SameSite=Lax, Max-Age=900 (15 min)
  - `refresh_token`: httpOnly, Secure (prod), SameSite=Lax, Max-Age=2592000 (30 days)
  - Return body: `RecruiterResponse` only (no tokens in body)
- `POST /auth/register` — same cookie-setting behaviour; return `RecruiterResponse`
- `POST /auth/refresh` — read `refresh_token` from cookie (not request body); issue new `access_token` cookie (and rotate `refresh_token` cookie); return `204` or `RecruiterResponse`; remove `RefreshRequest` body schema
- `POST /auth/logout` — read `refresh_token` from cookie (not request body); revoke DB row; clear both cookies (`Max-Age=0`); remove `LogoutRequest` body schema

**`backend/app/deps.py`:**
- Replace `HTTPBearer` with `Cookie` parameter: read `access_token` from request cookies
- `get_current_recruiter(access_token: str = Cookie(None), ...)` — decode and validate the cookie value; raise 401 if missing or invalid
- Remove `bearer_scheme`

**`backend/app/schemas/auth.py`:**
- Remove `RefreshRequest`, `LogoutRequest`
- Remove `refresh_token` from `TokenResponse` (or retire `TokenResponse` entirely — login/register now return `RecruiterResponse`)

**`backend/app/main.py` CORS:**
- `allow_origins` must be an explicit list (no `"*"`) when `allow_credentials=True` — already enforced via `CORS_ORIGINS` env var; verify this is set correctly in all environments

### 2. Strengths and Gaps Storage

**`backend/app/models/application.py`:**
- Add `strengths = Column(JSONB)` — stores `string[]` from `FIT_SCHEMA`
- Add `gaps = Column(JSONB)` — stores `string[]` from `FIT_SCHEMA`

**`backend/alembic/versions/`:**
- New migration: `ALTER TABLE candidate_job_applications ADD COLUMN strengths JSONB, ADD COLUMN gaps JSONB`

**`backend/app/schemas/application.py`:**
- `ApplicationResponse`: add `strengths: Optional[List[str]] = None`, `gaps: Optional[List[str]] = None`
- `ApplicationSummaryResponse`: no change needed (summary doesn't show strengths/gaps)
- `ResumeUploadResponse`: add `strengths: Optional[List[str]] = None`, `gaps: Optional[List[str]] = None`

**`backend/app/services/resume_service.py`** (or wherever `score_fit` result is persisted):
- Store `fit_result['strengths']` and `fit_result['gaps']` in `CandidateJobApplication` row alongside `fit_score` and `fit_explanation`
- Include `strengths` and `gaps` in `ResumeUploadResponse`

**`backend/app/schemas/candidate.py`** (candidate response with application):
- Application blocks in `CandidateWithApplicationResponse` and `CandidateJobCandidateResponse` should include `strengths` and `gaps`

### 3. AI Re-score Endpoint (supports retry without re-upload)

**`backend/app/api/candidates.py`:**
- New route: `POST /candidates/{candidate_id}/applications/{application_id}/rescore`
- Auth-protected; validates the application belongs to the recruiter's candidate
- Fetches the stored S3 key from the `CandidateJobApplication` row; raises 400 if `resume_key` is null (no resume uploaded yet)
- Calls `resume_service.score_fit(s3_key, job)` (or equivalent) — re-runs only the scoring step, not parsing
- Updates `fit_score`, `fit_explanation`, `strengths`, `gaps`, `ai_status` on the application row
- Returns same shape as `ResumeUploadResponse` (minus `resume_url` — resume is unchanged)

---

## Technical Context (Enrichment — 2026-06-28)

> Full report: [gappeo-frontend-enrichment.md](gappeo-frontend-enrichment.md)

### Critical Pre-conditions (must fix before frontend)

| # | Issue | Severity |
|---|-------|----------|
| 1 | `deps.py` uses `HTTPBearer` — every authenticated route will 401 in cookie mode | **HIGH** |
| 2 | `strengths`/`gaps` returned by AI but not persisted (no DB columns, discarded in `resume_service`) | **HIGH** |
| 3 | `CandidateWithApplicationResponse` is flat — PRD expects nested `application: {...}` object | **HIGH** |
| 4 | `ResumeUploadResponse` returns `parsed_resume` key; PRD TypeScript interface uses `ai_parsed_resume` | **HIGH** |
| 5 | `ai_status` field missing from all response schemas | **MEDIUM** |
| 6 | Resume upload path is `POST /candidates/:id/resume` (no `appId`); PRD expects `appId` in path | **MEDIUM** |
| 7 | Rescore endpoint does not exist | **MEDIUM** |

### Schema changes needed (backend → frontend contract)

```python
# CandidateJobApplication model — add:
strengths = Column(JSONB)        # string[]
gaps = Column(JSONB)             # string[]
ai_status = Column(String(20))   # 'complete' | 'failed'

# ResumeUploadResponse — rename + add:
ai_parsed_resume: Optional[Dict]   # was 'parsed_resume'
strengths: Optional[List[str]]
gaps: Optional[List[str]]
ai_status: str                     # always present

# CandidateWithApplicationResponse — reshape to nested:
application: {
  id, job_id, job_title, status, fit_score, fit_explanation,
  strengths, gaps, ai_parsed_resume, ai_status, applied_at
}
```

### Complexity
- **Overall: L (Large)**
- Backend pre-frontend: **M** | Frontend: **L** | Infrastructure: none
- Uncertainty: **Low** — PRD fully specified; shape mismatches are the only unknowns

### Implementation Order
1. Backend pre-frontend changes (all 9 changes, one PR)
2. Frontend scaffold → Auth pages → Jobs pages → Candidates list → Add Candidate → Candidate Detail
