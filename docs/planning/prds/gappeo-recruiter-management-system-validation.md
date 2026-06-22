---
prd: gappeo-recruiter-management-system
validated_at: "2026-06-22T00:00:00Z"
status: validated
overall_score: 81
previous_score: 52
---

# Validation Report: gappeo-recruiter-management-system

**Checklist:** all
**Status:** `needs-revision` (52% — threshold is 70%)

## Scores

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Problem Statement | 72/100 | Clear narrative but no quantified impact metrics |
| User Definition | 45/100 | Single persona, no goals/pain points, no HR vs. agency differentiation |
| Functional Requirements | 68/100 | Good ID coverage; ambiguous language in JOB-5 ("etc."), CAND-7 ("explains why"), BONUS undefined |
| Non-Functional Requirements | 18/100 | No performance targets, pagination, rate limiting, token expiry, or scalability |
| Security Considerations | 22/100 | Only route protection; no file upload validation, no authz model, no PII/GDPR note |
| Acceptance Criteria | 61/100 | Behavior-level criteria exist but not measurable; no AI quality or error-state criteria |
| **Overall Completeness** | **52%** | Below 70% threshold |

## Gaps (by implementability impact)

1. **No authorization model** — single-tenant vs. multi-tenant is undefined; wrong assumption requires schema/API rewrite
2. **No data model / field definitions** — Job and Candidate entities have zero field specs; blocks schema and API contract design
3. **No file upload security** — no MIME type, no size limit; CAND-5 as written is an exploitable open upload endpoint
4. **No JWT/session lifecycle** — token TTL, refresh strategy, and revocation are absent; blocks AUTH implementation decisions
5. **AI output contract undefined** — no structured fields list, no score range, no explanation format, no fallback behavior; blocks FE-4
6. **No pagination requirements** — undefined behavior for list endpoints at any data volume
7. **No error state requirements** — no spec for AI API downtime, malformed files, duplicate registration, DB failures
8. **Deployment platform unspecified** — different platforms have different Docker Compose and persistent storage support
9. **No password policy** — AUTH-1 has no minimum complexity or hashing requirement
10. **BONUS items have no definition of done** — CAND-8 and DOC-3 cannot be evaluated as complete

## Recommended Actions (prioritized)

1. Define authorization model explicitly (shared workspace vs. per-recruiter isolation)
2. Add data dictionary for Job and Candidate (fields, types, required/optional)
3. Replace CAND-6/CAND-7 with testable requirements: define AI output schema, score range, explanation format, fallback
4. Add file upload security requirement: accepted MIME types (PDF/DOCX), max size, server-side validation
5. Resolve JWT lifecycle: access token TTL, refresh token in/out of scope, logout requirement
6. Add NFR section: response time targets (AI vs. non-AI endpoints), default pagination size
7. Name deployment platform or add constraint (e.g., "must support Docker Compose with persistent PostgreSQL")
8. Add password policy to AUTH-1 (min length, bcrypt hashing)
9. Define BONUS acceptance criteria or remove from PRD
10. Add GDPR/PII scope note (even "demo only, not for production PII" is sufficient)

## Questions for Product Owner

1. **Authorization:** Can Recruiter A view/modify jobs and candidates created by Recruiter B? Shared workspace or isolated accounts?
2. **AI output:** What fields should the resume parser extract? What is the fit score range/format? What does the UI show when the AI API fails?
3. **Data model:** What fields are required on Job and Candidate? Which are mandatory vs. optional?
4. **File upload:** What file types are acceptable? Is there a maximum file size?
5. **JWT lifecycle:** How long should access tokens be valid? Is logout (token invalidation) required? Are refresh tokens in scope?
6. **Deployment:** Is there a preferred platform, or does the implementer choose within "free-tier" constraints?
7. **Pagination:** Should job/candidate lists be paginated? What is the default page size?
8. **Candidate stages:** Is there a concept of candidate status (Applied, Screened, Interviewed, Rejected, Hired)?
9. **Multi-job candidates:** Can a candidate be linked to multiple jobs, or always 1:1 with a job opening?
10. **AI performance:** What is the acceptable response time for the AI scoring endpoint? Is a loading state required?
