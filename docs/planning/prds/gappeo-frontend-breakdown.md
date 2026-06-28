---
prd: gappeo-frontend
breakdown_at: "2026-06-28T00:00:00Z"
target_size: 4-8h
includes_tests: true
linear_sync: false
---

# Work Breakdown: gappeo-frontend

**Items:** 15 | **Test Tickets:** 2 | **Target Size:** 4-8h
**Total Estimate:** 79–107h (≈ 10–13 days solo)

---

## Summary Table

| ID | Title | Area | Size | Priority | Depends On |
|----|-------|------|------|----------|------------|
| WI-001 | Migration 0004 — strengths/gaps/ai_status columns | Backend | 2-3h | P0 | — |
| WI-002 | Cookie auth migration | Backend | 4-6h | P0 | — |
| WI-003 | Strengths/gaps persistence + schema alignment | Backend | 4-6h | P1 | WI-001 |
| WI-004 | CandidateWithApplication response reshape | Backend | 4-6h | P1 | WI-001 |
| WI-005 | Rescore endpoint + resume upload path fix | Backend | 4-6h | P1 | WI-001, WI-003 |
| WI-006 | Frontend scaffold — Vite/Tailwind/routing/Axios/AuthContext | Frontend | 4-6h | P1 | WI-002 |
| WI-007 | Login + Register pages | Frontend | 3-5h | P2 | WI-006 |
| WI-008 | Jobs list page — filters + infinite scroll | Frontend | 6-8h | P2 | WI-006 |
| WI-009 | Job form page — create + edit + close | Frontend | 6-8h | P2 | WI-006 |
| WI-010 | Candidates list page — infinite scroll + fit score badges | Frontend | 4-6h | P3 | WI-004, WI-008 |
| WI-011 | Add Candidate page — two-step flow | Frontend | 6-8h | P3 | WI-005, WI-010 |
| WI-012 | Candidate Detail page — pipeline, resume, AI panel | Frontend | 8-12h | P3 | WI-005, WI-010 |
| WI-013 | Backend test updates (post-schema changes) | Testing | 3-5h | P1 | WI-002, WI-003, WI-004, WI-005 |
| WI-014 | Frontend integration + smoke tests | Testing | 6-8h | P4 | WI-007, WI-009, WI-012 |
| WI-015 | README.md | Docs | 1-2h | P4 | WI-014 |

---

## Dependency Graph

```
WI-001 ──┬──> WI-003 ──> WI-005 ──┬──> WI-011
          │                         └──> WI-012
          └──> WI-004 ──────────────────> WI-010 ──┬──> WI-011
                                                     └──> WI-012

WI-002 ──> WI-006 ──┬──> WI-007
                     ├──> WI-008 ──> WI-010
                     └──> WI-009

WI-002 + WI-003 + WI-004 + WI-005 ──> WI-013

WI-007 + WI-009 + WI-012 ──> WI-014 ──> WI-015
```

**Critical path:** WI-001 → WI-003 → WI-005 → WI-012 → WI-014 → WI-015
(≈ 31–43h of sequential-minimum work)

---

## Backend Work Items

### WI-001 — Migration 0004: strengths/gaps/ai_status columns
**Area:** Backend | **Size:** 2-3h | **Priority:** P0 | **Blocks:** WI-003, WI-004

#### Overview
Add three new columns to `candidate_job_applications` to support strengths/gaps persistence and AI status tracking. This is a prerequisite for all backend schema changes.

#### Deliverables
- New Alembic migration file `backend/alembic/versions/0004_strengths_gaps_ai_status.py`
  ```sql
  ALTER TABLE candidate_job_applications
    ADD COLUMN strengths JSONB,
    ADD COLUMN gaps JSONB,
    ADD COLUMN ai_status VARCHAR(20);
  ```
- Migration is idempotent and downgrade-safe (columns dropped on downgrade)

#### Definition of Done
- [ ] Migration file created under `alembic/versions/`
- [ ] `alembic upgrade head` runs without error against local Postgres
- [ ] `alembic downgrade -1` reverses cleanly
- [ ] `CandidateJobApplication` SQLAlchemy model updated with `strengths`, `gaps`, `ai_status` columns

---

### WI-002 — Cookie auth migration
**Area:** Backend | **Size:** 4-6h | **Priority:** P0 | **Blocks:** WI-006

#### Overview
Replace the current `HTTPBearer` + body token pattern with httpOnly cookie auth. This is the single highest-priority change — without it every authenticated frontend request will fail.

#### Deliverables
- **`backend/app/deps.py`**
  - Remove `HTTPBearer` + `bearer_scheme`
  - `get_current_recruiter(access_token: str = Cookie(None), db=...)` — decode cookie value; raise 401 if missing/invalid
- **`backend/app/api/auth.py`**
  - `POST /auth/login` — set `access_token` (Max-Age=900, httpOnly, Secure prod, SameSite=Lax) and `refresh_token` (Max-Age=2592000) cookies; return `RecruiterResponse` body only
  - `POST /auth/register` — same cookie behavior; return `RecruiterResponse` (201)
  - `POST /auth/refresh` — read `refresh_token` cookie (no body); issue new cookies; return 204
  - `POST /auth/logout` — read `refresh_token` cookie; revoke DB row; set both cookies with `Max-Age=0`; return 204
- **`backend/app/schemas/auth.py`**
  - Remove `RefreshRequest`, `LogoutRequest`, `TokenResponse`
  - `RegisterRequest.name` field: change to `Optional[str] = None` (name is optional per PRD register form)

#### Definition of Done
- [ ] `GET /jobs` returns 200 when `access_token` cookie is present; returns 401 when cookie is absent
- [ ] `POST /auth/login` response has `Set-Cookie: access_token=...; HttpOnly` header
- [ ] `POST /auth/refresh` (no body) rotates cookies and returns 204
- [ ] `POST /auth/logout` clears both cookies (Max-Age=0)
- [ ] No existing route still accepts `Authorization: Bearer` header (old deps removed)
- [ ] CORS: `allow_credentials=True` + explicit `CORS_ORIGINS` — confirmed no wildcard origin

---

### WI-003 — Strengths/gaps persistence + schema alignment
**Area:** Backend | **Size:** 4-6h | **Priority:** P1 | **Depends On:** WI-001 | **Blocks:** WI-005, WI-013

#### Overview
Wire `strengths[]` and `gaps[]` from `FIT_SCHEMA` through to the DB and all response schemas. Also rename `parsed_resume` → `ai_parsed_resume` in `ResumeUploadResponse` to match the PRD TypeScript interface.

#### Deliverables
- **`backend/app/services/resume_service.py`**
  - In `upload_and_analyze`: persist `fit_result['strengths']` and `fit_result['gaps']` on the application row
  - Set `app.ai_status = 'complete'` on scoring success; `app.ai_status = 'failed'` on exception (currently left as empty)
  - Return `strengths`, `gaps`, `ai_status` in result dict
- **`backend/app/schemas/application.py`**
  - `ResumeUploadResponse`: rename `parsed_resume` → `ai_parsed_resume`; add `strengths: Optional[List[str]] = None`, `gaps: Optional[List[str]] = None`, `ai_status: str`
  - `ApplicationResponse`: add `strengths: Optional[List[str]] = None`, `gaps: Optional[List[str]] = None`, `ai_status: Optional[str] = None`
  - `ApplicationSummaryResponse`: no change needed

#### Definition of Done
- [ ] Uploading a resume populates `strengths`, `gaps`, `ai_status` in the `candidate_job_applications` row (verified via psql)
- [ ] `POST /candidates/:id/applications/:appId/resume` response JSON includes `ai_parsed_resume`, `strengths`, `gaps`, `ai_status`
- [ ] `ai_status` is `"complete"` when AI succeeds, `"failed"` when it fails
- [ ] `strengths` and `gaps` are `null` (not empty array) when AI fails

---

### WI-004 — CandidateWithApplication response reshape
**Area:** Backend | **Size:** 4-6h | **Priority:** P1 | **Depends On:** WI-001 | **Blocks:** WI-010, WI-013

#### Overview
Reshape `CandidateWithApplicationResponse` from a flat struct to a nested `application: {...}` object matching the PRD TypeScript interface. Also add `ai_status`, `strengths`, `gaps`, `ai_parsed_resume`, `job_title` to the nested block.

#### Deliverables
- **`backend/app/schemas/candidate.py`** — rewrite `CandidateWithApplicationResponse`:
  ```python
  class ApplicationInCandidateList(BaseModel):
      id: UUID
      job_id: UUID
      job_title: Optional[str] = None
      status: str
      fit_score: Optional[int] = None
      fit_explanation: Optional[str] = None
      strengths: Optional[List[str]] = None
      gaps: Optional[List[str]] = None
      ai_parsed_resume: Optional[Dict[str, Any]] = None
      ai_status: Optional[str] = None
      applied_at: datetime

  class CandidateWithApplicationResponse(BaseModel):
      id: UUID
      name: str
      email: str
      phone: Optional[str] = None
      location_preference: Optional[str] = None
      linkedin_url: Optional[str] = None
      portfolio_url: Optional[str] = None
      github_url: Optional[str] = None
      resume_url: Optional[str] = None
      created_at: datetime
      application: ApplicationInCandidateList
  ```
- Update `candidate_service.py` query that builds this response to populate the nested structure

#### Definition of Done
- [ ] `GET /jobs/:jobId/candidates` response items have nested `application: { id, job_id, job_title, status, fit_score, ... }` object
- [ ] `resume_url` is a presigned URL (not raw S3 key)
- [ ] Existing tests updated to match new shape

---

### WI-005 — Rescore endpoint + resume upload path fix
**Area:** Backend | **Size:** 4-6h | **Priority:** P1 | **Depends On:** WI-001, WI-003 | **Blocks:** WI-011, WI-012, WI-013

#### Overview
Add the rescore endpoint and fix the resume upload route to include `application_id` in the path (needed so the backend knows which application's `ai_parsed_resume` to use for scoring).

#### Deliverables
- **`backend/app/api/candidates.py`**
  - Rename `POST /candidates/{candidate_id}/resume` → `POST /candidates/{candidate_id}/applications/{application_id}/resume`
    - Fetch the application row to get the existing `ai_parsed_resume` (if any); upload file; re-score against the application's job
    - Update `candidate.resume_s3_key` + application `ai_parsed_resume`, `fit_score`, `fit_explanation`, `strengths`, `gaps`, `ai_status`
  - Add `POST /candidates/{candidate_id}/applications/{application_id}/rescore`:
    - Verify candidate belongs to current recruiter
    - Fetch application; raise `400` if `resume_s3_key` is null
    - Download PDF from S3; run `ai_service.score_fit(job, existing_ai_parsed_resume)` (skip parse — use stored data)
    - Update `fit_score`, `fit_explanation`, `strengths`, `gaps`, `ai_status` on application
    - Return `RescoreResponse` (same shape as `ResumeUploadResponse` minus `resume_url`)
- **`backend/app/schemas/application.py`** — add `RescoreResponse` schema

#### Definition of Done
- [ ] `POST /candidates/:id/applications/:appId/resume` (new path) uploads and scores; returns `ResumeUploadResponse` shape
- [ ] `POST /candidates/:id/applications/:appId/rescore` (no body) re-scores using stored PDF; returns `RescoreResponse`
- [ ] Rescore returns 400 if no resume has been uploaded yet
- [ ] Rescore updates all four fields: `fit_score`, `fit_explanation`, `strengths`, `gaps`
- [ ] Old route `POST /candidates/:id/resume` removed (or returns 404)

---

### WI-013 — Backend test updates
**Area:** Testing | **Size:** 3-5h | **Priority:** P1 | **Depends On:** WI-002, WI-003, WI-004, WI-005

#### Overview
Update existing backend test suite to work with cookie auth, new response shapes, and new endpoints. Existing tests that send `Authorization: Bearer` headers will fail after WI-002.

#### Deliverables
- Update all test fixtures that set `Authorization: Bearer` to send `access_token` cookie instead
- Update assertions against `CandidateWithApplicationResponse` shape (flat → nested)
- Update assertions against `ResumeUploadResponse` (`parsed_resume` → `ai_parsed_resume`)
- Add tests for:
  - `POST /auth/login` sets `Set-Cookie` headers
  - `GET /jobs` returns 401 without cookie
  - `POST /candidates/:id/applications/:appId/rescore` success + 400 (no resume) paths

#### Definition of Done
- [ ] `pytest` passes with 0 failures after all backend WIs complete
- [ ] Cookie auth paths covered (login sets cookie, protected route reads cookie, logout clears cookie)
- [ ] Rescore endpoint has at least success + no-resume-uploaded test cases

---

## Frontend Work Items

### WI-006 — Frontend scaffold
**Area:** Frontend | **Size:** 4-6h | **Priority:** P1 | **Depends On:** WI-002 | **Blocks:** WI-007, WI-008, WI-009

#### Overview
Create the full frontend project structure: `src/` directory, Tailwind config, React Router skeleton, Axios client with cookie auth + 401 interceptor, AuthContext with session restore, and ProtectedLayout.

#### Deliverables
- `src/` directory created under `frontend/`
- **Tailwind CSS** configured (`tailwind.config.js`, `postcss.config.js`, `src/index.css`)
- **Packages installed:**
  ```
  npm install react-router-dom @tanstack/react-query axios react-hook-form zod react-markdown dompurify
  npm install -D @types/dompurify
  ```
- **`src/api/client.ts`** — Axios instance per PRD spec:
  - `baseURL: import.meta.env.VITE_API_URL || '/api'`
  - `withCredentials: true`
  - Response interceptor: on 401 → POST `/auth/refresh` (no body) once → retry; on second 401 → call `logout()` + redirect `/login`
- **`src/context/AuthContext.tsx`** — `{ recruiter, isAuthenticated, login, logout }`
  - App load: call `POST /auth/refresh`; on success set `isAuthenticated=true`; on failure set `isAuthenticated=false`
  - `login(recruiterResponse)` — store recruiter in context; no token storage
  - `logout()` — POST `/auth/logout`; reset context; navigate to `/login`
- **`src/main.tsx`** — `QueryClientProvider` + `AuthProvider` + `BrowserRouter`
- **`src/App.tsx`** — Route table with `ProtectedLayout` per PRD route table
- **`src/components/ProtectedLayout.tsx`** — redirects to `/login` if `!isAuthenticated`; shows `<Navbar>` + `<Outlet>`
- **`src/components/Navbar.tsx`** — logo, Jobs link, Logout button

#### Definition of Done
- [ ] `npm run dev` starts without errors
- [ ] `docker-compose up` serves frontend at `http://localhost` (Nginx proxies correctly)
- [ ] Navigating to `/jobs` while unauthenticated redirects to `/login`
- [ ] `POST /auth/refresh` called on app load; result drives `isAuthenticated`
- [ ] Axios instance sends cookies (`withCredentials: true`) — confirmed in browser DevTools Network tab
- [ ] 401 interceptor retries once via `/auth/refresh` before logging out

---

### WI-007 — Login + Register pages
**Area:** Frontend | **Size:** 3-5h | **Priority:** P2 | **Depends On:** WI-006

#### Overview
Implement the two auth forms. Cookie tokens are set by the server — the frontend only needs to call `login(recruiterResponse)` to populate AuthContext.

#### Deliverables
- **`src/api/auth.ts`** — `loginApi(email, password)`, `registerApi(email, password, name?)`, `logoutApi()`
- **`src/pages/LoginPage.tsx`**
  - Centered card layout (Tailwind)
  - `LoginForm`: email + password fields, RHF + Zod (`email` required valid format, `password` min 8)
  - On success: call `login(recruiterResponse)` → navigate to `/jobs`
  - On error: inline error message below the form
  - Link to Register page
- **`src/pages/RegisterPage.tsx`**
  - Same layout as Login
  - `RegisterForm`: email, password, name (optional), RHF + Zod
  - On success: call `login(recruiterResponse)` → navigate to `/jobs`
  - Link to Login page

#### Definition of Done
- [ ] Login form validates email format + min 8 password; shows field-level errors
- [ ] Successful login stores recruiter in AuthContext and redirects to `/jobs`
- [ ] Failed login (wrong credentials) shows API error message; no token stored
- [ ] Register creates account and redirects to `/jobs`
- [ ] No token in `localStorage`, `sessionStorage`, or JS-accessible cookie
- [ ] Login and Register pages are accessible from each other via link

---

### WI-008 — Jobs list page
**Area:** Frontend | **Size:** 6-8h | **Priority:** P2 | **Depends On:** WI-006 | **Blocks:** WI-010

#### Overview
Implement the Jobs list with 7 filters and cursor-based infinite scroll. This is the default post-login destination.

#### Deliverables
- **`src/api/jobs.ts`** — `listJobs(params)`, `getJob(id)`, `createJob(data)`, `updateJob(id, data)`, `closeJob(id)`
- **`src/pages/JobsPage.tsx`**
  - `JobFilters` component: status select, title text (debounced 300ms via `setTimeout` + `useEffect`), department text, location text, employment_type select, experience_level select, remote_type select
  - `useInfiniteQuery` with query key `['jobs', filters]`; `pageParam` → `cursor` query param
  - `IntersectionObserver` sentinel div at list bottom → `fetchNextPage()` when visible
  - `JobCard`: title (bold), department, location, status badge (green=open, gray=closed), `{candidate_count} candidates`, created date (formatted)
  - Click card → navigate to `/jobs/:jobId`
  - "+ New Job" button → navigate to `/jobs/new`
  - Empty state: "No jobs found" with "+ New Job" CTA
  - Loading state: 3 skeleton cards (`animate-pulse`)

#### Definition of Done
- [ ] Changing any filter re-fetches from page 1 (query key changes)
- [ ] Infinite scroll loads next page when sentinel enters viewport; stops when `next_cursor` is null
- [ ] Debounced title search fires ≥ 300ms after last keystroke
- [ ] Status badge color correct (green / gray)
- [ ] Navigating to `/jobs/new` and back preserves filter state (React Query cache)

---

### WI-009 — Job form page (create + edit + close)
**Area:** Frontend | **Size:** 6-8h | **Priority:** P2 | **Depends On:** WI-006

#### Overview
Single `JobForm` component used in both create and edit modes. Includes tag input for `required_skills` and the close job action.

#### Deliverables
- **`src/pages/JobFormPage.tsx`** — detects create vs edit mode from route params
- **`src/components/JobForm.tsx`** — all fields per PRD Zod table:
  - `title` (required, max 200), `description` (required textarea), `department` (max 100), `location` (max 100)
  - `salary_min`, `salary_max` (positive integer; Zod refine: `salary_max >= salary_min` if both present)
  - `required_skills`: **tag input** — `onKeyDown` intercepts Enter and comma; adds tag to `string[]` via `Array.from(new Set([...tags, trimmedInput]))`; Backspace on empty input removes last tag; max 30 tags; renders tags as chips with × remove
  - `employment_type`, `experience_level`, `remote_type` selects
  - In edit mode only: status select + "Close Job" button (PATCH `/jobs/:id/close`)
- Create: `POST /jobs` → `navigate('/jobs/' + newJob.id)`
- Edit: pre-fill form from `useQuery(['job', jobId])`; `PUT /jobs/:id` → success toast → stay on page; invalidate `['jobs']` + `['job', jobId]`
- "Close Job": `PATCH /jobs/:id/close` → update UI immediately; show success toast

#### Definition of Done
- [ ] Required fields (title, description) show field-level Zod errors on submit
- [ ] Salary cross-field validation: error if `salary_max < salary_min`
- [ ] Tag input: Enter/comma commits; Backspace removes last; duplicates silently dropped; max 30 enforced
- [ ] Create redirects to `/jobs/:newId` after success
- [ ] Edit pre-fills all fields from fetched job; success toast shown; query cache invalidated
- [ ] Close Job updates status badge without full page reload

---

### WI-010 — Candidates list page
**Area:** Frontend | **Size:** 4-6h | **Priority:** P3 | **Depends On:** WI-004, WI-008

#### Overview
Candidates list for a specific job — sorted by fit score descending, infinite scroll, fit score color badges.

#### Deliverables
- **`src/api/candidates.ts`** — `listCandidates(jobId, cursor?)`, `getCandidate(id)`, `createCandidate(data)`, `updateCandidate(id, data)`, `deleteCandidate(id)`, `createApplication(candidateId, jobId)`, `updateStatus(candidateId, appId, status)`, `uploadResume(candidateId, appId, file)`, `rescore(candidateId, appId)`
- **`src/pages/CandidatesPage.tsx`**
  - Breadcrumb: `Jobs > {job.title} > Candidates`
  - Job summary header: title, status badge, department/location, salary range, `required_skills` chips
  - `useInfiniteQuery` with key `['candidates', jobId]`
  - IntersectionObserver sentinel → `fetchNextPage()`
  - `CandidateCard`: name, email, `current_title` / `current_company` from `application.ai_parsed_resume` (if present), fit score badge, pipeline status badge
  - Fit score badge colors: green (≥ 70), yellow (40–69), red (< 40), gray (no score)
  - Click card → navigate to `/jobs/:jobId/candidates/:candidateId`
  - "+ Add Candidate" → navigate to `/jobs/:jobId/candidates/new`
  - Empty state: "No candidates yet" with "+ Add Candidate" CTA

#### Definition of Done
- [ ] List sorted by fit_score desc; unscored candidates appear at bottom (backend handles ordering)
- [ ] Fit score badge color matches spec (green/yellow/red/gray)
- [ ] `current_title` pulled from `application.ai_parsed_resume.current_title` when available
- [ ] Infinite scroll works correctly; no double-fetch on mount
- [ ] Job summary header shows all fields; salary shown as range (e.g. "$60k – $90k") or "Not specified"

---

### WI-011 — Add Candidate page (two-step flow)
**Area:** Frontend | **Size:** 6-8h | **Priority:** P3 | **Depends On:** WI-005, WI-010

#### Overview
Two-step flow: optional resume upload first, then candidate form. Three sequential API calls on submit. Mid-flow failure redirects to candidate detail with a warning toast.

#### Deliverables
- **`src/pages/AddCandidatePage.tsx`**
  - Step 1 — Resume upload (optional):
    - PDF file input, client-side size check ≤ 5 MB (show error if exceeded)
    - "Skip" button to go to Step 2 without a file
    - Selected filename shown if file picked
  - Step 2 — Candidate form (RHF + Zod per PRD validation table):
    - `name`*, `email`*, phone, location_preference, linkedin_url (valid URL), portfolio_url (valid URL), github_url (valid URL), expected_salary_min, expected_salary_max (≥ min if both), notice_period_days (non-negative int), source, notes
  - On submit:
    1. `POST /candidates` → `candidate`
    2. `POST /candidates/:id/applications` `{ job_id }` → `application`
    3. If file selected: `POST /candidates/:id/applications/:appId/resume` (multipart) with spinner "Parsing resume with AI…"
       - If `ai_status === 'failed'`: show warning toast; navigate to detail page
       - On success: navigate to detail page
    4. If no file: navigate to `/jobs/:jobId/candidates/:candidateId`
  - If step 3 fails after steps 1–2 succeed: navigate to `/jobs/:jobId/candidates/:candidateId` with warning toast "Resume upload failed — you can retry from the candidate detail page"

#### Definition of Done
- [ ] Required fields (name, email) show Zod field errors on submit
- [ ] File > 5 MB shows client-side error before any API call
- [ ] "Skip" bypasses resume step; candidate created with no resume
- [ ] Spinner with "Parsing resume with AI…" visible during resume upload
- [ ] `ai_status === 'failed'` shows warning toast and still navigates to detail page
- [ ] Mid-flow failure (resume upload network error) redirects to detail page with warning — candidate not lost
- [ ] URL validation errors shown for linkedin/portfolio/github fields

---

### WI-012 — Candidate Detail page
**Area:** Frontend | **Size:** 8-12h | **Priority:** P3 | **Depends On:** WI-005, WI-010

#### Overview
Most complex page. Four distinct sections: contact info, pipeline selector (optimistic), resume section (upload + retry), AI panel (score gauge + explanation + strengths/gaps + parsed resume accordion), and other applications list.

#### Deliverables
- **`src/pages/CandidateDetailPage.tsx`**
- **Header:** name, email, phone, location_preference, icon links (LinkedIn, portfolio, GitHub) with `rel="noopener noreferrer" target="_blank"`
- **Pipeline selector:** `<select>` with all 5 statuses; on change → optimistic update (TanStack Query v5 `onMutate`/`onError` rollback) → PATCH status; on failure: revert to previous value + error toast
- **Resume section:**
  - If `resume_url`: "View Resume" link (`target="_blank" rel="noopener noreferrer"`) + "Re-upload" button
  - If no resume: "Upload Resume" button
  - File input (hidden, triggered by button); client-side 5 MB check; `POST .../resume` multipart; spinner; on success invalidate `['candidate', id]`
  - If `ai_status === 'failed'` and resume exists: "Retry AI scoring" button → `POST .../rescore`; spinner; on success invalidate query
- **AI Panel** (shown only when `fit_score !== null || ai_parsed_resume !== null`):
  - Fit score: large number + color ring/gauge (green ≥ 70, yellow 40–69, red < 40)
  - `fit_explanation` rendered via `<ReactMarkdown>` (default plugins — no `rehype-raw`)
  - Strengths: green check icons, shown only when `strengths?.length > 0`
  - Gaps: orange warning icons, shown only when `gaps?.length > 0`
  - Parsed resume accordion (collapsible sections): Summary (ReactMarkdown), Skills chips, Experience timeline, Education list, total_experience_years
- **Other applications:** `application_summaries[]` — job title, status badge, fit_score badge — each is a `<Link to="/jobs/:job_id/candidates/:candidateId">` (same-tab SPA navigation; `:candidateId` is the current page's candidate id)

#### Definition of Done
- [ ] Pipeline selector updates optimistically; reverts on PATCH failure + shows error toast
- [ ] Resume upload shows spinner; on success AI panel appears/updates without page reload
- [ ] "Retry AI scoring" button visible only when `ai_status === 'failed'` and `resume_url` exists
- [ ] AI panel hidden entirely when `fit_score === null && ai_parsed_resume === null`
- [ ] `fit_explanation` and resume summary rendered as markdown (not plain text)
- [ ] Strengths/gaps lists hidden when arrays are empty (not shown as empty)
- [ ] All external links have `rel="noopener noreferrer" target="_blank"`
- [ ] "Other applications" links navigate in same tab (no `target="_blank"`)
- [ ] Presigned resume URL opens PDF in new tab

---

### WI-014 — Frontend integration + smoke tests
**Area:** Testing | **Size:** 6-8h | **Priority:** P4 | **Depends On:** WI-007, WI-009, WI-012

#### Overview
Smoke-level integration tests covering the critical user journeys using Vitest + Testing Library (or Playwright for E2E if preferred).

#### Deliverables
- Auth flow: login → redirect to `/jobs` → logout → redirect to `/login`
- Jobs: create job → appears in list → edit job → close job
- Candidate: add candidate (with resume skip) → appears in list → open detail → advance pipeline stage
- AI retry: mock `ai_status: 'failed'` response → retry button visible → click → panel updates
- Axios interceptor: mock 401 → verify refresh called once → retry → success

#### Definition of Done
- [ ] All 5 smoke test scenarios pass
- [ ] Tests run via `npm test` with no manual setup
- [ ] No tests rely on real API (mocked with MSW or vi.mock)

---

### WI-015 — README.md
**Area:** Docs | **Size:** 1-2h | **Priority:** P4 | **Depends On:** WI-014

#### Overview
Write the project README covering setup, environment variables, and the main features.

#### Deliverables
- Project overview + tech stack
- Quick start: `docker-compose up` + local dev commands
- Environment variables table (mirrors `.env.example`)
- Feature list with screenshots (optional)
- Deployment notes (Render + Cloudflare R2)

#### Definition of Done
- [ ] `docker-compose up` instructions accurate and tested
- [ ] All env vars in `.env.example` documented in README
- [ ] Render deploy steps documented

---

## Parallelization Opportunities

Once WI-001 is merged:
- **WI-002 and WI-003 can run in parallel** (different files; WI-002 = auth layer, WI-003 = resume service + schemas)
- **WI-004 can run in parallel with WI-002 and WI-003** (candidate schemas only)
- After WI-006 is complete, **WI-007, WI-008, WI-009 can all run in parallel**

Minimum elapsed time with full parallelism:
```
WI-001 (2-3h) → WI-002 || WI-003 || WI-004 (4-6h each, parallel) → WI-005 (4-6h) → WI-006 (4-6h) → WI-007 || WI-008 || WI-009 (6-8h each, parallel) → WI-010 (4-6h) → WI-011 || WI-012 (8-12h each, parallel) → WI-013 + WI-014 → WI-015
```
≈ **38–51h wall clock** with a team of 2–3 engineers

---

## Total Estimate

| Area | Items | Low | High |
|------|-------|-----|------|
| Backend | 5 | 18h | 27h |
| Frontend | 7 | 37h | 53h |
| Testing | 2 | 9h | 13h |
| Docs | 1 | 1h | 2h |
| **Total** | **15** | **65h** | **95h** |

Solo engineer at 6h/day productive: **~11–16 days**
