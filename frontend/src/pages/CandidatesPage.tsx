import React, { useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useInfiniteQuery } from '@tanstack/react-query'
import { getJob, listJobCandidates } from '../api/jobs'
import type { CandidateWithApplicationResponse, PipelineStatus } from '../types'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const PENDING_LABELS: Record<PipelineStatus, string> = {
  applied: 'Awaiting Screening',
  screened: 'Awaiting Interview',
  interviewed: 'Descision Pending',
  hired: 'Hired',
  rejected: 'Not Proceeding',
}

function formatLabel(value: string): string {
  return PENDING_LABELS[value as PipelineStatus] ?? value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatSalary(min?: number, max?: number): string | null {
  if (!min && !max) return null
  const fmt = (n: number) =>
    n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${n}`
  if (min && max) return `${fmt(min)} – ${fmt(max)}`
  if (min) return `${fmt(min)}+`
  return `up to ${fmt(max!)}`
}

// ---------------------------------------------------------------------------
// Fit score badge
// ---------------------------------------------------------------------------
function FitBadge({ score }: { score?: number | null }) {
  if (score == null) {
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500">
        No score
      </span>
    )
  }
  const colorClass =
    score >= 70
      ? 'bg-green-600 text-white'
      : score >= 40
      ? 'bg-yellow-400 text-yellow-900'
      : 'bg-red-500 text-white'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium tabular-nums ${colorClass}`}>
      {score}%
    </span>
  )
}

// ---------------------------------------------------------------------------
// Pipeline status badge
// ---------------------------------------------------------------------------
const STATUS_COLORS: Record<PipelineStatus, string> = {
  applied: 'bg-blue-100 text-blue-700',
  screened: 'bg-yellow-100 text-yellow-700',
  interviewed: 'bg-purple-100 text-purple-700',
  rejected: 'bg-red-100 text-red-700',
  hired: 'bg-green-100 text-green-700',
}

function StatusBadge({ status }: { status: PipelineStatus }) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[status]}`}
    >
      {formatLabel(status)}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Candidate card
// ---------------------------------------------------------------------------
function CandidateCard({
  candidate,
  jobId,
}: {
  candidate: CandidateWithApplicationResponse
  jobId: string
}) {
  const navigate = useNavigate()
  const { application } = candidate

  // Pull current_title / current_company from ai_parsed_resume JSON if present
  let currentTitle: string | undefined
  let currentCompany: string | undefined
  if (application.ai_parsed_resume) {
    try {
      const parsed =
        typeof application.ai_parsed_resume === 'string'
          ? JSON.parse(application.ai_parsed_resume)
          : application.ai_parsed_resume
      currentTitle = parsed?.current_title ?? parsed?.title ?? undefined
      currentCompany = parsed?.current_company ?? parsed?.company ?? undefined
    } catch {
      // ignore malformed JSON
    }
  }

  return (
    <button
      type="button"
      onClick={() => navigate(`/jobs/${jobId}/candidates/${candidate.id}`)}
      className="w-full text-left bg-white border border-gray-200 rounded-lg p-5 hover:border-blue-300 hover:shadow-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left: name + meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-0.5">
            <span className="text-base font-semibold text-gray-900 leading-snug">
              {candidate.name}
            </span>
            <StatusBadge status={application.status} />
            <FitBadge score={application.fit_score} />
          </div>
          <p className="text-sm text-gray-500">{candidate.email}</p>
          {(currentTitle || currentCompany) && (
            <p className="text-sm text-gray-400 mt-1">
              {[currentTitle, currentCompany].filter(Boolean).join(' · ')}
            </p>
          )}
        </div>
        {/* Chevron */}
        <svg
          className="w-4 h-4 text-gray-300 flex-shrink-0 mt-1"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </button>
  )
}

// ---------------------------------------------------------------------------
// Skeleton card
// ---------------------------------------------------------------------------
function SkeletonCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 animate-pulse">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-4 bg-gray-200 rounded w-32" />
            <div className="h-5 bg-gray-100 rounded-full w-16" />
            <div className="h-5 bg-gray-100 rounded-full w-10" />
          </div>
          <div className="h-3 bg-gray-100 rounded w-44" />
        </div>
        <div className="w-4 h-4 bg-gray-100 rounded" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Job header skeleton
// ---------------------------------------------------------------------------
function JobHeaderSkeleton() {
  return (
    <div className="mb-8 animate-pulse">
      <div className="h-3 bg-gray-200 rounded w-48 mb-3" />
      <div className="flex items-center gap-3 mb-2">
        <div className="h-7 bg-gray-200 rounded w-64" />
        <div className="h-5 bg-gray-100 rounded-full w-14" />
      </div>
      <div className="flex gap-3 mb-4">
        <div className="h-3 bg-gray-100 rounded w-24" />
        <div className="h-3 bg-gray-100 rounded w-20" />
        <div className="h-3 bg-gray-100 rounded w-16" />
      </div>
      <div className="flex gap-2">
        <div className="h-6 bg-gray-100 rounded w-16" />
        <div className="h-6 bg-gray-100 rounded w-20" />
        <div className="h-6 bg-gray-100 rounded w-14" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function CandidatesPage() {
  const { jobId } = useParams<{ jobId: string }>()

  const { data: job, isLoading: jobLoading } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJob(jobId!),
    enabled: Boolean(jobId),
  })

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['candidates', jobId],
    queryFn: ({ pageParam }) =>
      listJobCandidates(jobId!, (pageParam as string | null) ?? undefined),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    initialPageParam: null as string | null,
    enabled: Boolean(jobId),
  })

  const candidates: CandidateWithApplicationResponse[] =
    data?.pages.flatMap((page) => page.data) ?? []

  // Infinite scroll sentinel
  const sentinelRef = useRef<HTMLDivElement | null>(null)

  const handleIntersect = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
        fetchNextPage()
      }
    },
    [hasNextPage, isFetchingNextPage, fetchNextPage]
  )

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel) return
    const observer = new IntersectionObserver(handleIntersect, { rootMargin: '200px' })
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [handleIntersect])

  const salary = job ? formatSalary(job.salary_min, job.salary_max) : null

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">

      {/* Job header */}
      {jobLoading ? (
        <JobHeaderSkeleton />
      ) : job ? (
        <div className="mb-8">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-1.5 text-sm text-gray-400 mb-3" aria-label="Breadcrumb">
            <Link to="/jobs" className="hover:text-blue-600 transition-colors">
              Jobs
            </Link>
            <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
            <Link to={`/jobs/${jobId}`} className="hover:text-blue-600 transition-colors truncate max-w-[200px]">
              {job.title}
            </Link>
            <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
            <span className="text-gray-500">Candidates</span>
          </nav>

          {/* Title + status */}
          <div className="flex items-center gap-3 flex-wrap mb-2">
            <h1
              className="text-2xl font-semibold text-gray-900 leading-tight"
              style={{ textWrap: 'balance' } as React.CSSProperties}
            >
              {job.title}
            </h1>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                job.status === 'open'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              {formatLabel(job.status)}
            </span>
          </div>

          {/* Meta row */}
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-500 mb-4">
            {job.department && (
              <span className="flex items-center gap-1">
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16" />
                </svg>
                {job.department}
              </span>
            )}
            {job.location && (
              <span className="flex items-center gap-1">
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {job.location}
              </span>
            )}
            {job.employment_type && <span>{formatLabel(job.employment_type)}</span>}
            {job.experience_level && <span>{formatLabel(job.experience_level)}</span>}
            {job.remote_type && <span>{formatLabel(job.remote_type)}</span>}
            {salary && (
              <span className="flex items-center gap-1 tabular-nums">
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {salary}
              </span>
            )}
          </div>

          {/* Skills chips */}
          {job.required_skills.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {job.required_skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {/* Candidates section header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Candidates</h2>
        <Link
          to={`/jobs/${jobId}/candidates/new`}
          className="inline-flex items-center gap-1.5 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          Add Candidate
        </Link>
      </div>

      {/* Error state */}
      {isError && (
        <div className="text-center py-16">
          <p className="text-red-600 font-medium mb-1">Failed to load candidates</p>
          <p className="text-sm text-gray-500">Check your connection and try refreshing.</p>
        </div>
      )}

      {/* Initial loading skeletons */}
      {isLoading && (
        <div className="space-y-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && candidates.length === 0 && (
        <div className="text-center py-20">
          <svg
            className="mx-auto w-12 h-12 text-gray-300 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z"
            />
          </svg>
          <p className="text-gray-500 text-lg font-medium mb-1">No candidates yet</p>
          <p className="text-gray-400 text-sm mb-6">Add your first candidate to start building the pipeline.</p>
          <Link
            to={`/jobs/${jobId}/candidates/new`}
            className="inline-flex items-center gap-1.5 bg-blue-600 text-white px-5 py-2.5 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
            Add Candidate
          </Link>
        </div>
      )}

      {/* Candidate list */}
      {!isLoading && !isError && candidates.length > 0 && (
        <div className="space-y-3">
          {candidates.map((c) => (
            <CandidateCard key={c.id} candidate={c} jobId={jobId!} />
          ))}
        </div>
      )}

      {/* Load-more skeletons while fetching next page */}
      {isFetchingNextPage && (
        <div className="space-y-3 mt-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Infinite scroll sentinel */}
      <div ref={sentinelRef} className="h-1" aria-hidden="true" />
    </div>
  )
}
