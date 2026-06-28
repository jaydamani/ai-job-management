import React, { useRef, useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { candidatesApi, applicationsApi } from '../api/candidates'
import type { PipelineStatus, ApplicationSummaryResponse } from '../types'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const STATUS_COLORS: Record<PipelineStatus, string> = {
  applied:    'bg-blue-100 text-blue-700',
  screened:   'bg-yellow-100 text-yellow-700',
  interviewed:'bg-purple-100 text-purple-700',
  rejected:   'bg-red-100 text-red-700',
  hired:      'bg-green-100 text-green-700',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatLabel(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

function getNextStage(current: PipelineStatus): PipelineStatus | null {
  const order: PipelineStatus[] = ['applied', 'screened', 'interviewed', 'hired']
  const idx = order.indexOf(current)
  if (idx === -1 || idx === order.length - 1) return null
  return order[idx + 1]
}

const PENDING_LABELS: Record<PipelineStatus, string> = {
  applied: 'Awaiting Screening',
  screened: 'Awaiting Interview',
  interviewed: 'Descision Pending',
  hired: 'Hired',
  rejected: 'Not Proceeding',
}

const ACTION_LABELS: Record<PipelineStatus, string> = {
  applied: 'Move to Interview',
  screened: 'Schedule Interview',
  interviewed: 'Send Offer',
  hired: '',
  rejected: '',
}

// ---------------------------------------------------------------------------
// AI data shape (extended from upload/rescore responses, stored in state)
// ---------------------------------------------------------------------------
interface AiState {
  fit_score?: number
  fit_explanation?: string
  strengths?: string[]
  gaps?: string[]
  ai_parsed_resume?: string
  ai_status?: string
  resume_url?: string
}

// ---------------------------------------------------------------------------
// Fit score ring
// ---------------------------------------------------------------------------
function FitScoreRing({ score }: { score: number }) {
  const color =
    score >= 70 ? '#16a34a' : score >= 40 ? '#d97706' : '#dc2626'
  const bg =
    score >= 70 ? '#dcfce7' : score >= 40 ? '#fef3c7' : '#fee2e2'
  const size = 88
  const stroke = 7
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ

  return (
    <div
      className="relative inline-flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`AI fit score: ${score} out of 100`}
    >
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={bg} strokeWidth={stroke}
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
        />
      </svg>
      <div
        className="absolute inset-0 flex flex-col items-center justify-center"
        style={{ fontVariantNumeric: 'tabular-nums' }}
      >
        <span className="text-2xl font-bold leading-none" style={{ color }}>
          {score}
        </span>
        <span className="text-xs text-gray-400 leading-none mt-0.5">/ 100</span>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Parsed resume accordion
// ---------------------------------------------------------------------------
interface ParsedResume {
  summary?: string
  skills?: string[]
  experience?: Array<{ title?: string; company?: string; duration?: string }>
  education?: Array<{ degree?: string; institution?: string; year?: string }>
  total_experience_years?: number
  current_title?: string
  current_company?: string
}

function ResumeAccordion({ raw }: { raw: string }) {
  const [open, setOpen] = useState(false)
  const [parsed, setParsed] = useState<ParsedResume | null>(null)

  useEffect(() => {
    try {
      const data = typeof raw === 'string' ? JSON.parse(raw) : raw
      setParsed(data)
    } catch {
      setParsed(null)
    }
  }, [raw])

  if (!parsed) return null

  const hasContent =
    parsed.summary ||
    (parsed.skills && parsed.skills.length > 0) ||
    (parsed.experience && parsed.experience.length > 0) ||
    (parsed.education && parsed.education.length > 0)

  if (!hasContent) return null

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500 text-left"
        aria-expanded={open}
      >
        <span className="text-sm font-medium text-gray-700">Parsed Resume</span>
        <div className="flex items-center gap-2">
          {parsed.total_experience_years != null && (
            <span className="text-xs text-gray-500 tabular-nums">
              {parsed.total_experience_years}y exp
            </span>
          )}
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {open && (
        <div className="px-4 py-4 space-y-5 divide-y divide-gray-100">
          {parsed.summary && (
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Summary</p>
              <div className="prose prose-sm max-w-none text-gray-700 text-sm leading-relaxed">
                <ReactMarkdown>{parsed.summary}</ReactMarkdown>
              </div>
            </div>
          )}

          {parsed.skills && parsed.skills.length > 0 && (
            <div className="pt-4">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Skills</p>
              <div className="flex flex-wrap gap-1.5">
                {parsed.skills.map((skill, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-medium"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {parsed.experience && parsed.experience.length > 0 && (
            <div className="pt-4">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Experience</p>
              <div className="space-y-2">
                {parsed.experience.map((exp, i) => (
                  <div key={i} className="text-sm">
                    <span className="font-medium text-gray-800">{exp.title}</span>
                    {exp.company && (
                      <span className="text-gray-500"> · {exp.company}</span>
                    )}
                    {exp.duration && (
                      <span className="text-gray-400 text-xs ml-1">({exp.duration})</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {parsed.education && parsed.education.length > 0 && (
            <div className="pt-4">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Education</p>
              <div className="space-y-2">
                {parsed.education.map((edu, i) => (
                  <div key={i} className="text-sm">
                    {edu.degree && (
                      <span className="font-medium text-gray-800">{edu.degree}</span>
                    )}
                    {edu.institution && (
                      <span className="text-gray-500"> · {edu.institution}</span>
                    )}
                    {edu.year && (
                      <span className="text-gray-400 text-xs ml-1">({edu.year})</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Skeleton
// ---------------------------------------------------------------------------
function DetailSkeleton() {
  return (
    <div className="max-w-5xl mx-auto py-8 px-4 animate-pulse">
      {/* Breadcrumb */}
      <div className="flex gap-2 mb-6">
        <div className="h-3 bg-gray-200 rounded w-12" />
        <div className="h-3 bg-gray-200 rounded w-3" />
        <div className="h-3 bg-gray-200 rounded w-24" />
        <div className="h-3 bg-gray-200 rounded w-3" />
        <div className="h-3 bg-gray-200 rounded w-20" />
        <div className="h-3 bg-gray-200 rounded w-3" />
        <div className="h-3 bg-gray-200 rounded w-28" />
      </div>
      {/* Header */}
      <div className="mb-8">
        <div className="h-7 bg-gray-200 rounded w-48 mb-2" />
        <div className="h-4 bg-gray-100 rounded w-36 mb-1" />
        <div className="h-4 bg-gray-100 rounded w-28" />
      </div>
      {/* Body */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3 space-y-4">
          <div className="h-32 bg-gray-100 rounded-lg" />
          <div className="h-48 bg-gray-100 rounded-lg" />
        </div>
        <div className="lg:col-span-2 space-y-4">
          <div className="h-40 bg-gray-100 rounded-lg" />
          <div className="h-24 bg-gray-100 rounded-lg" />
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function CandidateDetailPage() {
  const { jobId, candidateId } = useParams<{ jobId: string; candidateId: string }>()
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: candidate, isLoading, isError } = useQuery({
    queryKey: ['candidate', candidateId],
    queryFn: () => candidatesApi.get(candidateId!),
    enabled: Boolean(candidateId),
  })

  const appSummary = candidate?.applications.find((a) => a.job_id === jobId)

  // Extended AI state — ApplicationSummaryResponse doesn't carry strengths/gaps/ai_parsed_resume/ai_status
  // We hold them in component state, seeded from appSummary on mount and updated from mutation responses.
  const [aiState, setAiState] = useState<AiState>({})
  const [localStatus, setLocalStatus] = useState<PipelineStatus | null>(null)

  // Seed AI state once appSummary lands (or changes)
  useEffect(() => {
    if (appSummary) {
      setAiState({
        fit_score: appSummary.fit_score,
        fit_explanation: appSummary.fit_explanation,
        resume_url: appSummary.resume_url,
        // strengths/gaps/ai_parsed_resume/ai_status not in summary — start empty
      })
      setLocalStatus(appSummary.status)
    }
  }, [appSummary?.id])

  // Upload resume
  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      candidatesApi.uploadResume(candidateId!, appSummary!.id, file),
    onSuccess: (res) => {
      setAiState({
        fit_score: res.fit_score,
        fit_explanation: res.fit_explanation,
        strengths: res.strengths,
        gaps: res.gaps,
        ai_parsed_resume: res.ai_parsed_resume,
        ai_status: res.ai_status,
        resume_url: res.resume_url,
      })
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] })
      toast.success('Resume uploaded')
    },
    onError: () => toast.error('Upload failed'),
  })

  // Rescore
  const rescoreMutation = useMutation({
    mutationFn: () => candidatesApi.rescore(candidateId!, appSummary!.id),
    onSuccess: (res) => {
      setAiState((prev) => ({
        ...prev,
        fit_score: res.fit_score,
        fit_explanation: res.fit_explanation,
        strengths: res.strengths,
        gaps: res.gaps,
        ai_parsed_resume: res.ai_parsed_resume,
        ai_status: res.ai_status,
      }))
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] })
      toast.success('Scoring complete')
    },
    onError: () => toast.error('Rescoring failed'),
  })

  // Status update with optimistic update
  const prevStatusRef = useRef<PipelineStatus | null>(null)
  const statusMutation = useMutation({
    mutationFn: (status: PipelineStatus) =>
      applicationsApi.updateStatus(appSummary!.id, status),
    onSuccess: (res) => {
      setLocalStatus(res.status)
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] })
      queryClient.invalidateQueries({ queryKey: ['candidates', jobId] })
      toast.success('Status updated')
    },
    onError: () => {
      if (prevStatusRef.current) setLocalStatus(prevStatusRef.current)
      toast.error('Failed to update status')
    },
  })

  function handleStatusChange(next: PipelineStatus) {
    prevStatusRef.current = localStatus
    setLocalStatus(next)
    statusMutation.mutate(next)
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File must be under 5 MB')
      e.target.value = ''
      return
    }
    uploadMutation.mutate(file)
    e.target.value = ''
  }

  // ---------------------------------------------------------------------------
  // Loading / error states
  // ---------------------------------------------------------------------------
  if (isLoading) return <DetailSkeleton />

  if (isError || !candidate) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-4">
        <div className="text-center py-20">
          <p className="text-red-600 font-medium mb-1">Failed to load candidate</p>
          <p className="text-sm text-gray-500">Check your connection and try refreshing.</p>
        </div>
      </div>
    )
  }

  const currentStatus = localStatus ?? appSummary?.status ?? 'applied'
  const otherApps = candidate.applications.filter((a) => a.job_id !== jobId)
  const currentApp = appSummary

  const effectiveResumeUrl = aiState.resume_url ?? currentApp?.resume_url
  const hasScore = aiState.fit_score != null
  const hasAiData = hasScore || aiState.ai_parsed_resume != null
  const aiStatusFailed = aiState.ai_status === 'failed' && effectiveResumeUrl

  // Link URLs
  const externalLinks: Array<{ label: string; url: string }> = [
    candidate.linkedin_url ? { label: 'LinkedIn', url: candidate.linkedin_url } : null,
    candidate.portfolio_url ? { label: 'Portfolio', url: candidate.portfolio_url } : null,
    candidate.github_url ? { label: 'GitHub', url: candidate.github_url } : null,
  ].filter(Boolean) as Array<{ label: string; url: string }>

  const jobTitle = currentApp?.job_title

  return (
    <div className="max-w-5xl mx-auto py-8 px-4">

      {/* Breadcrumb */}
      <nav className="flex items-center gap-1.5 text-sm text-gray-400 mb-6 flex-wrap" aria-label="Breadcrumb">
        <Link to="/jobs" className="hover:text-blue-600 transition-colors">Jobs</Link>
        <ChevronIcon />
        {jobTitle ? (
          <Link to={`/jobs/${jobId}/candidates`} className="hover:text-blue-600 transition-colors truncate max-w-[160px]">
            {jobTitle}
          </Link>
        ) : (
          <Link to={`/jobs/${jobId}/candidates`} className="hover:text-blue-600 transition-colors">
            Candidates
          </Link>
        )}
        {jobTitle && (
          <>
            <ChevronIcon />
            <Link to={`/jobs/${jobId}/candidates`} className="hover:text-blue-600 transition-colors">
              Candidates
            </Link>
          </>
        )}
        <ChevronIcon />
        <span className="text-gray-600 truncate max-w-[160px]">{candidate.name}</span>
      </nav>

      {/* Candidate header */}
      <div className="mb-8">
        <h1
          className="text-2xl font-semibold text-gray-900 leading-tight mb-1"
          style={{ textWrap: 'balance' } as React.CSSProperties}
        >
          {candidate.name}
        </h1>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-gray-500">
          <span>{candidate.email}</span>
          {candidate.phone && <span>{candidate.phone}</span>}
          {candidate.location_preference && (
            <span className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              {candidate.location_preference}
            </span>
          )}
        </div>
        {externalLinks.length > 0 && (
          <div className="flex items-center gap-3 mt-2">
            {externalLinks.map(({ label, url }) => (
              <a
                key={label}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline transition-colors"
              >
                {label}
                <svg className="w-3 h-3 opacity-60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">

        {/* Left column — resume + AI */}
        <div className="lg:col-span-4 space-y-5">

          {/* Candidate detail card */}
          <section className="bg-white border border-gray-200 rounded-lg p-5">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">Candidate Info</h2>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
              {candidate.expected_salary_min || candidate.expected_salary_max ? (
                <div>
                  <dt className="text-gray-500 mb-0.5">Expected Salary</dt>
                  <dd className="text-gray-900 font-medium tabular-nums">
                    {formatSalaryRange(candidate.expected_salary_min, candidate.expected_salary_max)}
                  </dd>
                </div>
              ) : null}
              {candidate.notice_period_days != null && (
                <div>
                  <dt className="text-gray-500 mb-0.5">Notice Period</dt>
                  <dd className="text-gray-900 font-medium tabular-nums">{candidate.notice_period_days} days</dd>
                </div>
              )}
              {candidate.source && (
                <div>
                  <dt className="text-gray-500 mb-0.5">Source</dt>
                  <dd className="text-gray-900 font-medium">{formatLabel(candidate.source)}</dd>
                </div>
              )}
              {candidate.notes && (
                <div className="sm:col-span-2">
                  <dt className="text-gray-500 mb-0.5">Notes</dt>
                  <dd className="text-gray-700 leading-relaxed">{candidate.notes}</dd>
                </div>
              )}
              <div>
                <dt className="text-gray-500 mb-0.5">Added</dt>
                <dd className="text-gray-900 font-medium">{formatDate(candidate.created_at)}</dd>
              </div>
              {currentApp && (
                <div className="sm:col-span-2 pt-3 border-t border-gray-100">
                  <dt className="text-gray-500 mb-1.5">Pipeline</dt>
                  <dd>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[currentStatus]}`}>
                        {PENDING_LABELS[currentStatus]}
                      </span>
                      {currentStatus !== 'rejected' && currentStatus !== 'hired' && (
                        <>
                          <button
                            type="button"
                            onClick={() => {
                              const nextStatus = getNextStage(currentStatus)
                              if (nextStatus) handleStatusChange(nextStatus)
                            }}
                            disabled={statusMutation.isPending}
                            className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                          >
                            {statusMutation.isPending ? (
                              <><SpinnerIcon /> Processing…</>
                            ) : (
                              <>{ACTION_LABELS[currentStatus]}</>
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => handleStatusChange('rejected')}
                            disabled={statusMutation.isPending}
                            className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded border border-red-200 bg-white hover:bg-red-50 text-red-600 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                          >
                            Reject
                          </button>
                        </>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-1.5 tabular-nums">
                      Applied {formatDate(currentApp.applied_at)}
                    </p>
                  </dd>
                </div>
              )}
            </dl>
          </section>

          {/* Resume section */}
          {currentApp && (
            <section className="bg-white border border-gray-200 rounded-lg p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Resume</h2>
                <div className="flex items-center gap-2">
                  {effectiveResumeUrl && (
                    <a
                      href={effectiveResumeUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline"
                    >
                      View PDF
                      <svg className="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                      </svg>
                    </a>
                  )}
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploadMutation.isPending}
                    className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded border border-gray-200 bg-white hover:bg-gray-50 text-gray-600 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  >
                    {uploadMutation.isPending ? (
                      <>
                        <SpinnerIcon />
                        Uploading…
                      </>
                    ) : effectiveResumeUrl ? (
                      'Re-upload'
                    ) : (
                      'Upload PDF'
                    )}
                  </button>
                </div>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileChange}
              />

              {/* No resume yet */}
              {!effectiveResumeUrl && !uploadMutation.isPending && (
                <div className="flex flex-col items-center py-8 text-center border-2 border-dashed border-gray-200 rounded-lg">
                  <svg className="w-8 h-8 text-gray-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m6.75 12l-3-3m0 0l-3 3m3-3v6m-1.5-15H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                  <p className="text-sm text-gray-500">No resume uploaded yet</p>
                  <p className="text-xs text-gray-400 mt-0.5">PDF, max 5 MB</p>
                </div>
              )}

              {/* PDF preview */}
              {effectiveResumeUrl && (
                <div className="mt-4">
                  <div className="rounded-lg border border-gray-200 overflow-hidden bg-gray-50">
                    <iframe
                      src={effectiveResumeUrl}
                      title="Resume PDF preview"
                      className="w-full border-0"
                      style={{ height: '85vh', minHeight: '600px' }}
                    />
                  </div>
                </div>
              )}

              {/* AI status indicators */}
              {aiState.ai_status && aiState.ai_status !== 'completed' && aiState.ai_status !== 'failed' && (
                <div className="flex items-center gap-2 mt-3 text-sm text-gray-500">
                  <SpinnerIcon />
                  <span>AI scoring {aiState.ai_status}…</span>
                </div>
              )}

              {/* Retry scoring */}
              {aiStatusFailed && (
                <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-lg flex items-center justify-between gap-3">
                  <p className="text-sm text-red-700">AI scoring failed.</p>
                  <button
                    type="button"
                    onClick={() => rescoreMutation.mutate()}
                    disabled={rescoreMutation.isPending}
                    className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded border border-red-200 bg-white text-red-700 hover:bg-red-50 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
                  >
                    {rescoreMutation.isPending ? (
                      <><SpinnerIcon /> Rescoring…</>
                    ) : (
                      'Retry AI Scoring'
                    )}
                  </button>
                </div>
              )}

              {/* Resume rescore button when no failure */}
              {effectiveResumeUrl && !aiStatusFailed && (
                <div className="mt-3 flex items-center justify-end">
                  <button
                    type="button"
                    onClick={() => rescoreMutation.mutate()}
                    disabled={rescoreMutation.isPending}
                    className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                  >
                    {rescoreMutation.isPending ? (
                      <><SpinnerIcon /> Rescoring…</>
                    ) : (
                      'Rescore with AI'
                    )}
                  </button>
                </div>
              )}
            </section>
          )}

          {/* AI panel */}
          {hasAiData && (
            <section className="bg-white border border-gray-200 rounded-lg p-5">
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-4">AI Assessment</h2>

              {/* Score + explanation */}
              <div className="flex gap-5 mb-5">
                {aiState.fit_score != null && (
                  <FitScoreRing score={aiState.fit_score} />
                )}
                {aiState.fit_explanation && (
                  <div className="flex-1 min-w-0 prose prose-sm max-w-none text-gray-700 text-sm leading-relaxed">
                    <ReactMarkdown>{aiState.fit_explanation}</ReactMarkdown>
                  </div>
                )}
              </div>

              {/* Strengths + Gaps */}
              {((aiState.strengths && aiState.strengths.length > 0) ||
                (aiState.gaps && aiState.gaps.length > 0)) && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                  {aiState.strengths && aiState.strengths.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Strengths</p>
                      <ul className="space-y-1.5">
                        {aiState.strengths.map((s, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                            <span className="mt-0.5 text-green-500 flex-shrink-0" aria-hidden="true">✓</span>
                            {s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {aiState.gaps && aiState.gaps.length > 0 && (
                    <div>
                      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Gaps</p>
                      <ul className="space-y-1.5">
                        {aiState.gaps.map((g, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                            <span className="mt-0.5 text-amber-500 flex-shrink-0" aria-hidden="true">⚠</span>
                            {g}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Parsed resume accordion */}
              {aiState.ai_parsed_resume && (
                <div className="mt-4">
                  <ResumeAccordion raw={aiState.ai_parsed_resume} />
                </div>
              )}
            </section>
          )}

        </div>

        {/* Right column — other applications */}
        {/* <div className="lg:col-span-1 space-y-5">

          {otherApps.length > 0 && (
            <section className="bg-white border border-gray-200 rounded-lg p-5">
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Other Applications ({otherApps.length})
              </h2>
              <div className="space-y-2">
                {otherApps.map((app) => (
                  <OtherAppRow key={app.id} app={app} candidateId={candidateId!} />
                ))}
              </div>
            </section>
          )}

        </div> */}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Other application row
// ---------------------------------------------------------------------------
function OtherAppRow({
  app,
  candidateId,
}: {
  app: ApplicationSummaryResponse
  candidateId: string
}) {
  const statusColor = STATUS_COLORS[app.status] ?? 'bg-gray-100 text-gray-600'
  const scoreColor =
    app.fit_score == null
      ? 'bg-gray-100 text-gray-500'
      : app.fit_score >= 70
      ? 'bg-green-600 text-white'
      : app.fit_score >= 40
      ? 'bg-yellow-400 text-yellow-900'
      : 'bg-red-500 text-white'

  return (
    <Link
      to={`/jobs/${app.job_id}/candidates/${candidateId}`}
      className="flex items-center justify-between gap-3 p-2.5 rounded-lg border border-transparent hover:border-gray-200 hover:bg-gray-50 transition-all group focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <span className="text-sm text-gray-700 truncate group-hover:text-blue-600 transition-colors flex-1 min-w-0">
        {app.job_title ?? 'Untitled role'}
      </span>
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusColor}`}>
          {formatLabel(app.status)}
        </span>
        {app.fit_score != null && (
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium tabular-nums ${scoreColor}`}>
            {app.fit_score}%
          </span>
        )}
      </div>
    </Link>
  )
}

// ---------------------------------------------------------------------------
// Micro-components
// ---------------------------------------------------------------------------
function ChevronIcon() {
  return (
    <svg className="w-3 h-3 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
    </svg>
  )
}

function SpinnerIcon() {
  return (
    <svg
      className="w-3.5 h-3.5 animate-spin"
      fill="none" viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function formatSalaryRange(min?: number, max?: number): string {
  if (!min && !max) return '—'
  const fmt = (n: number) => n >= 1000 ? `$${Math.round(n / 1000)}k` : `$${n}`
  if (min && max) return `${fmt(min)} – ${fmt(max)}`
  if (min) return `${fmt(min)}+`
  return `up to ${fmt(max!)}`
}
