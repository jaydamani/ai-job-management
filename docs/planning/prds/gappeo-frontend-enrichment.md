---
prd: gappeo-frontend
enriched_at: "2026-06-28T00:00:00Z"
depth: standard
status: complete
---

# Enrichment Report: gappeo-frontend

**Depth:** standard
**Analyst:** technical-analyst

---

## Codebase Pattern Analysis

### What already exists

| Area | Finding |
|------|---------|
| Frontend scaffold | `frontend/` directory exists with `node_modules` and `dist` only — **no `src/` yet**. Vite + React is installed (node_modules present) but no application code exists. |
| Backend API | Fully implemented at `backend/app/` — all 15 endpoints confirmed live. |
| Auth | Currently uses `HTTPBearer` + body token passing. **Cookie migration is required before frontend can function.** |
| AI service | `FIT_SCHEMA` already returns `strengths[]` + `gaps[]` but these fields are **not persisted** to DB and **not included** in any response schema. |
| Presigned URLs | `model_validator` pattern on `CandidateResponse` auto-generates presigned URL from `resume_s3_key` — this works correctly. |
| Pagination | Cursor-based (`base64(field|id)`) — `PaginatedResponse[T]` generic wrapper is reusable. |
| Application schema | `ApplicationResponse` and `ResumeUploadResponse` **missing `strengths`, `gaps`, `ai_parsed_resume` key name mismatch** (backend uses `parsed_resume`, PRD expects `ai_parsed_resume`). |
| Candidate schema | `CandidateWithApplicationResponse` is a flat struct (application fields flattened onto candidate row). PRD expects a nested `application: {...}` object inside each list item — **shape mismatch must be resolved in backend or adapted in frontend**. |
| Applications router | `POST /candidates/:id/applications/:appId/status` — the PATCH status endpoint is mounted at `/applications` router, not `/candidates`. Frontend PRD path `PATCH /candidates/:id/applications/:appId/status` is correct functionally but the actual mount is via `/applications` prefix. |
| Resume upload | Currently at `POST /candidates/:id/resume` (no `applications/:appId/` in path). PRD specifies `POST /candidates/:id/applications/:appId/resume`. **Path divergence** — backend needs update or frontend must use actual path. |
| Rescore endpoint | Does **not exist** yet. Must be added before frontend. |

---

## Risk Flags

| Severity | Area | Detail |
|----------|------|--------|
| **HIGH** | Cookie auth — blocking | `deps.py` uses `HTTPBearer`; all protected routes expect `Authorization: Bearer`. Frontend will get 403/422 on every authenticated request until cookie auth migration is complete. |
| **HIGH** | `strengths`/`gaps` not persisted | `ai_service.score_fit()` returns them; `resume_service.upload_and_analyze()` discards them. DB columns don't exist. Frontend will receive `null` for these fields until migration 0004 + schema updates. |
| **HIGH** | `CandidateWithApplicationResponse` shape mismatch | Backend returns flattened fields (`application_status`, `fit_score`, `applied_at` at top level). PRD TypeScript interface expects a nested `application: { id, job_id, job_title, status, ... }` object. Frontend will break or need an adapter layer. |
| **HIGH** | `ai_parsed_resume` key name | Backend `ResumeUploadResponse` returns `parsed_resume`; PRD interface uses `ai_parsed_resume`. Must align before frontend consumes the response. |
| **MEDIUM** | Resume upload path | Backend has `POST /candidates/:id/resume` (no `appId` in path). PRD specifies `POST /candidates/:id/applications/:appId/resume`. Either the backend route needs to change (preferred, since scoring needs the application) or frontend must use the existing path. |
| **MEDIUM** | `ApplicationResponse` has `updated_at` but no `job_title` | `ApplicationSummaryResponse` has `job_title`; `ApplicationResponse` (returned by `POST /applications`) does not. Frontend needs `job_title` in application blocks for CandidateWithApplications. |
| **MEDIUM** | CORS credentials | `allow_credentials=True` is set, `CORS_ORIGINS` is explicit — correct. But Render frontend URL must be added to `CORS_ORIGINS` env var at deploy time or all cross-origin cookie requests will be rejected. |
| **MEDIUM** | `ai_status` field missing from DB/responses | `CandidateWithApplicationResponse` and `ApplicationResponse` don't include `ai_status`. Frontend CandidateCard and AIPanel need this to show "Scoring failed" state and the retry button. |
| **LOW** | SameSite=Lax + Render cross-site | Render backend and frontend are separate subdomains (`*.onrender.com`). SameSite=Lax blocks cookies on cross-site POSTs (non-navigation). Must verify cookies use `SameSite=None; Secure` on Render or consolidate origins. |
| **LOW** | VITE_API_URL for Render | Static site must bake in the backend URL at build time. Missing env var = silent `/api` base → 404s on Render. |
| **LOW** | `candidate_count` on Job model | PRD shows `candidate_count` on `Job` interface. Need to confirm this is a DB column vs. computed — check job service/model. |
| **LOW** | `application_summaries` on CandidateWithApplication | PRD expects `application_summaries[]` on each item in the job candidates list. Backend `CandidateWithApplicationResponse` does not include this. Either add to backend or omit from CandidateCard (only needed on detail page). |

---

## Technical Notes

### Backend changes required before any frontend work

These are ordered by dependency (later items depend on earlier ones):

1. **Migration 0004** — `ALTER TABLE candidate_job_applications ADD COLUMN strengths JSONB, ADD COLUMN gaps JSONB, ADD COLUMN ai_status VARCHAR(20)`
2. **`CandidateJobApplication` model** — add `strengths`, `gaps`, `ai_status` columns
3. **`deps.py`** — replace `HTTPBearer` with `Cookie(None)` for `access_token`; remove `bearer_scheme`
4. **`auth.py`** — set `access_token` + `refresh_token` httpOnly cookies on login/register; read cookie on refresh/logout; return `RecruiterResponse` (no tokens in body)
5. **`schemas/auth.py`** — remove `RefreshRequest`, `LogoutRequest`, `TokenResponse`
6. **`schemas/application.py`** — add `strengths`, `gaps`, `ai_status` to `ApplicationResponse` and `ResumeUploadResponse`; rename `parsed_resume` → `ai_parsed_resume` in `ResumeUploadResponse`
7. **`schemas/candidate.py`** — reshape `CandidateWithApplicationResponse` to nested `application: {...}` object matching PRD TypeScript interface; add `job_title`, `ai_status`, `strengths`, `gaps`, `ai_parsed_resume` inside nested block
8. **`resume_service.py`** — persist `fit_result['strengths']`, `fit_result['gaps']`; set `ai_status='complete'/'failed'` on application row
9. **`candidates.py`** — add rescore route `POST /candidates/{id}/applications/{appId}/rescore`; update resume upload path to include `appId`

### Frontend scaffold status

The `frontend/` directory has Vite + React installed (from a prior `npm create vite` run) but **no `src/` directory exists** — the scaffold is effectively empty. All application code must be created from scratch.

### Existing reusable patterns

| Pattern | Location | Reuse in frontend |
|---------|----------|-------------------|
| Cursor pagination | `PaginatedResponse[T]` generic | `useInfiniteQuery` `pageParam` maps directly to `cursor` query param |
| Presigned URL generation | `model_validator` on `CandidateResponse` | Opaque to frontend — just consume `resume_url` from response |
| Enum values | `application_status_enum`, job filter enums | Mirror in Zod schemas and TypeScript `as const` objects |
| Cookie credentials | Backend will set `SameSite=Lax` | Axios `withCredentials: true` is the correct counterpart |

### AI response latency

`parse_resume` + `score_fit` are two sequential LLM calls. Combined wall-clock latency is typically 8–20 seconds depending on PDF size and model throughput. The resume upload spinner will be visible for this entire window. Consider:
- **Acceptable for MVP** — no polling needed; the POST blocks until both calls complete.
- If latency is unacceptable in testing, the backend could return immediately after upload and push scoring to a background task (out of scope for this sprint).

### IntersectionObserver for infinite scroll

No existing pattern in the codebase. Standard approach:
```tsx
const sentinelRef = useRef<HTMLDivElement>(null)
useEffect(() => {
  const obs = new IntersectionObserver(([e]) => {
    if (e.isIntersecting && hasNextPage) fetchNextPage()
  })
  if (sentinelRef.current) obs.observe(sentinelRef.current)
  return () => obs.disconnect()
}, [hasNextPage, fetchNextPage])
```

### Tag input (required_skills)

No existing component in codebase. Custom implementation needed — React Hook Form `Controller` wrapping an uncontrolled `<input>` that manages a `string[]` value. Pattern: `onKeyDown` intercepts Enter/comma, `Array.from(new Set([...tags, newTag]))` for dedup.

### Optimistic updates for pipeline status

TanStack Query v5 optimistic update pattern:
```tsx
const mutation = useMutation({
  mutationFn: (status) => updateStatus(candidateId, appId, status),
  onMutate: async (newStatus) => {
    await queryClient.cancelQueries({ queryKey: ['candidate', candidateId] })
    const prev = queryClient.getQueryData(['candidate', candidateId])
    queryClient.setQueryData(['candidate', candidateId], (old) => ({...old, application: {...old.application, status: newStatus}}))
    return { prev }
  },
  onError: (_, __, ctx) => {
    queryClient.setQueryData(['candidate', candidateId], ctx.prev)
    showErrorToast('Status update failed')
  },
  onSettled: () => queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] }),
})
```

### DOMPurify + react-markdown

Install: `npm install react-markdown dompurify && npm install -D @types/dompurify`

Safe pattern (avoids XSS via rehype-raw):
```tsx
import ReactMarkdown from 'react-markdown'
// Do NOT use rehype-raw — it re-enables HTML injection.
// react-markdown with default plugins strips raw HTML automatically.
// DOMPurify is a second-pass safety net for the rendered DOM string if needed.
<ReactMarkdown>{fit_explanation}</ReactMarkdown>
```

---

## Dependency Map

### Internal

| Dependency | Status | Blocks |
|------------|--------|--------|
| Cookie auth migration | Not started | Every authenticated frontend route |
| Strengths/gaps migration (0004) | Not started | AIPanel strengths/gaps display |
| `CandidateWithApplicationResponse` reshape | Not started | CandidatesPage list rendering |
| Rescore endpoint | Not started | Retry button on CandidateDetailPage |
| `ai_status` field in responses | Not started | AI fail state + retry affordance |

### External

| Service | SLA | Notes |
|---------|-----|-------|
| OpenRouter / Claude | ~99.9% | AI scoring failures are expected; graceful `ai_status='failed'` path handles them |
| Cloudflare R2 / MinIO | ~99.9% | Presigned URLs expire after 1 hour; mid-session expiry is rare |
| Render (deploy) | ~99.5% | No HA concern for this scope |

### Infrastructure

- No new infrastructure needed for frontend MVP
- Nginx config already handles `/*` → frontend:3000 — no changes needed
- Render static site requires `VITE_API_URL` set to backend Render URL at build time

---

## Complexity Estimate

| Component | Size | Notes |
|-----------|------|-------|
| Backend pre-frontend changes | **M** | 9 targeted file changes; no new services; migration is trivial |
| Frontend scaffold | **XS** | Vite already initialized; just need `src/` |
| Auth pages (Login, Register) | **XS** | Two simple forms; cookie auth removes token management entirely |
| Jobs pages (list + form) | **S** | Filters + infinite scroll + tag input; no novel complexity |
| Candidates list page | **S** | Infinite scroll + fit score badges; depends on backend shape fix |
| Add Candidate page | **M** | Two-step flow with conditional resume upload + 3 sequential API calls |
| Candidate Detail page | **M** | Most complex page: pipeline selector, resume upload, AI panel with accordion, other apps list |
| Axios client + interceptor | **XS** | Verbatim from PRD spec |
| AuthContext + session restore | **S** | App-load `POST /auth/refresh` + context wiring |
| **Overall** | **L** | Large but well-specified; no unknown unknowns after backend changes |

**Uncertainty: Low** — PRD is 93% validated with all blocking issues resolved. The only uncertainty is whether the `CandidateWithApplicationResponse` shape change breaks existing backend tests (likely yes — update tests alongside).

---

## Implementation Order

The safest sequence that avoids rework:

```
1. Backend pre-frontend changes (all 9 changes in one PR)
   ├── Migration 0004
   ├── Cookie auth (deps.py, auth.py, schemas/auth.py)
   ├── Strengths/gaps (model, schemas, resume_service)
   ├── CandidateWithApplicationResponse reshape
   └── Rescore endpoint
2. Frontend scaffold (src/ setup, Tailwind, routing skeleton)
3. Auth pages + AuthContext + Axios client
4. Jobs pages (list + form)
5. Candidates list page
6. Add Candidate page
7. Candidate Detail page (last — depends on all backend fields)
```

---

## Non-Blocking Recommendations

These are optional quality improvements that do not block launch:

- **AI panel hide condition:** When `ai_status === 'failed'` and `fit_score === null` and `ai_parsed_resume === null`, hide the entire AIPanel — the retry button in the Resume section is the sole affordance. Document this in code.
- **Skeleton loaders:** 3 skeleton cards per list page; use `animate-pulse` Tailwind class. No library needed.
- **Toast:** Fixed top-right, 4-second auto-dismiss, max 3 stacked. Implement as a lightweight reducer — no library.
- **Step back in AddCandidate:** If user returns to Step 1 (browser back or step indicator click), preserve the selected file in state; do not reset.
- **CSRF note:** SameSite=Lax provides CSRF protection for state-changing requests initiated by cross-site navigations. Add a comment in AuthContext explaining this so future engineers don't add redundant CSRF token logic.
