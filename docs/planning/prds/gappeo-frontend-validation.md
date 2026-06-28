---
prd: gappeo-frontend
validated_at: "2026-06-28T00:00:00Z"
overall_score: 93
status: validated
---

# Validation Report: gappeo-frontend

**Checklist:** all
**Validated:** 2026-06-28 (fourth pass — blocking localStorage bug fixed; non-blocking gaps documented)

## Scores

| Dimension | Score |
|-----------|-------|
| Problem Statement | 70/100 |
| User Definition | 72/100 |
| Acceptance Criteria | 87/100 |
| Security Considerations | 88/100 |
| Implementability | 93/100 |
| **Overall Completeness** | **93%** |

> All blocking issues resolved. PRD is implementation-ready.

---

## Resolution Summary

### Pass 1 → Pass 2 (PO questions resolved)

| # | Item | Status |
|---|------|--------|
| 1 | Strengths/gaps — added to API types + Backend Changes Required | ✅ |
| 2 | AI content rendering — react-markdown + dompurify | ✅ |
| 3 | `rel="noopener noreferrer"` in Constraints | ✅ |
| 4 | Interceptor multipart retry documented | ✅ |
| 5 | Mid-flow AddCandidate failure → redirect to detail page | ✅ |

### Pass 2 → Pass 3 (new gaps resolved)

| # | Item | Status |
|---|------|--------|
| N1 | Auth API table updated to cookie-based contract | ✅ |
| N2 | `CandidateWithApplications` written as complete TypeScript interface | ✅ |
| N3 | Optimistic rollback acceptance criterion added | ✅ |
| N4 | Tag input behavior specified (Enter/comma commits, backspace removes, duplicates dropped) | ✅ |
| N5 | Zod validation table added — Job, Candidate, and Login/Register forms | ✅ |
| N6 | AI retry = `POST /rescore` (server re-scores stored PDF, no re-upload); endpoint added to API contract + Backend Changes Required | ✅ |

### Pass 3 → Pass 4 (blocking bug fixed)

| # | Item | Status |
|---|------|--------|
| B-1 | LoginPage spec said "store access_token + refresh_token in localStorage" — stale line from pre-cookie draft; corrected to "cookies set by server; call login(recruiterResponse); redirect to /jobs" | ✅ Fixed |

---

## Remaining Open Items (non-blocking)

| # | Item | Severity |
|---|------|----------|
| AC-2 | No AC for app-load session restore (success path: valid refresh cookie → stays on /jobs; failure path: expired cookie → /login without auth flash) | Nice-to-have |
| AC-3 | Two-step AddCandidate: no spec for step-back behavior — file preservation, whether step indicator is clickable | Nice-to-have |
| S-2 | No explicit CSRF statement — SameSite=Lax rationale undocumented; engineer can add a comment in AuthContext | Nice-to-have |
| S-3 | Presigned URL expiry duration unspecified — silent S3 XML error if URL expires mid-session; backend configures 1-hour expiry per CLAUDE.md | Nice-to-have |
| I-2 | AIPanel render condition (`fit_score` or `ai_parsed_resume` exists) ambiguous when `ai_status==='failed'` and neither is present — hide panel or show "Scoring failed" placeholder? Default: hide panel; retry button in Resume section is the sole affordance | Nice-to-have |
| I-3 | ApplicationSummary links: source of `:candidateId` not explicit — it is the current candidate's `id` from the parent page/query; unambiguous in practice | Nice-to-have |
| 6 | Loading skeletons and empty-state specs | Nice-to-have |
| 7 | Toast mount point, auto-dismiss duration, stack behavior | Nice-to-have |
| 8 | ProtectedLayout redirect logic — driven by `isAuthenticated` from AuthContext (set by app-load `POST /auth/refresh`) | Nice-to-have |
| 10 | Volume/scale context (e.g. "up to 20 open roles, 200 candidates per role") | Nice-to-have |

These do not block implementation. Developers can make reasonable defaults (e.g. 3 skeleton cards, 4-second toast, top-right fixed, hide AI panel when no data).

---

## What's Strong

- Route table exhaustive and unambiguous
- API contract is fully implementation-ready — endpoint table, TypeScript interfaces, cookie auth contract, Zod schemas all present
- Acceptance criteria are binary and testable; optimistic rollback covered
- Component tree is concrete — every page and sub-component named
- Two-step AddCandidate flow fully specified including failure UX
- AI retry path is unambiguous — POST /rescore, no re-upload
- Backend Changes Required covers cookie auth, strengths/gaps persistence, and rescore endpoint
- Constraints are crisp with hard limits
- Security addressed: httpOnly cookies, DOMPurify sanitization, `rel` attributes, CORS enforced

---

## Questions for Product Owner — All Resolved

| # | Question | Answer |
|---|----------|--------|
| 1 | Where do strengths/gaps come from? | `FIT_SCHEMA` — `strengths: string[]`, `gaps: string[]`; backend migration + schema needed |
| 2 | Mid-flow add-candidate failure destination | Land on candidate detail; retry resume there |
| 3 | AI content rendering — plain text or markdown? | Markdown |
| 4 | `application_summaries` links — same tab or new tab? | Same tab (SPA navigation) |
| 5 | Token storage — localStorage or httpOnly cookies? | httpOnly cookies |
| N1 | Auth API table — body tokens or cookies? | Cookies; table updated |
| N2 | CandidateWithApplications type — complete interface needed | Written out in full |
| N3 | Optimistic rollback on PATCH failure? | Revert + error toast |
| N4 | Tag input behavior? | Enter/comma commits; backspace removes last; duplicates dropped |
| N5 | Zod validation rules? | Table added for all three forms |
| N6 | AI retry — re-upload or server re-score? | Server re-score via POST /rescore; new backend endpoint specified |
| B-1 | LoginPage spec had stale localStorage line | Fixed in PRD — cookies set by server, call login(), redirect /jobs |
