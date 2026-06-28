import React, { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useInfiniteQuery } from '@tanstack/react-query'
import { listJobs } from '../api/jobs'
import type { JobResponse } from '../types'

// ---------------------------------------------------------------------------
// Debounce hook
// ---------------------------------------------------------------------------
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatLabel(value: string): string {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

// ---------------------------------------------------------------------------
// Skeleton card
// ---------------------------------------------------------------------------
function SkeletonCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-3" />
      <div className="h-3 bg-gray-100 rounded w-1/2 mb-2" />
      <div className="h-3 bg-gray-100 rounded w-1/3 mb-4" />
      <div className="flex items-center justify-between">
        <div className="h-5 bg-gray-200 rounded-full w-16" />
        <div className="h-3 bg-gray-100 rounded w-20" />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Job card
// ---------------------------------------------------------------------------
function JobCard({ job }: { job: JobResponse }) {
  const navigate = useNavigate()

  return (
    <div className="bg-white border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all">
      <button
        type="button"
        onClick={() => navigate(`/jobs/${job.id}/candidates`)}
        className="w-full text-left p-5 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 rounded-t-lg"
      >
        <div className="flex items-start justify-between gap-2 mb-2">
          <h2 className="text-base font-semibold text-gray-900 leading-snug flex-1 min-w-0" style={{ textWrap: 'balance' } as React.CSSProperties}>
            {job.title}
          </h2>
          <span
            className={`flex-shrink-0 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
              job.status === 'open'
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {job.status}
          </span>
        </div>

        <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-gray-500 mb-4">
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
          {job.remote_type && (
            <span>{formatLabel(job.remote_type)}</span>
          )}
          {job.employment_type && (
            <span>{formatLabel(job.employment_type)}</span>
          )}
          {job.experience_level && (
            <span>{formatLabel(job.experience_level)}</span>
          )}
        </div>

        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400 tabular-nums">
            {formatDate(job.created_at)}
          </span>
          {job.required_skills.length > 0 && (
            <span className="text-xs text-gray-400">
              {job.required_skills.length} skill{job.required_skills.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </button>

      <div className="px-5 py-2.5 border-t border-gray-100 flex items-center justify-between">
        <Link
          to={`/jobs/${job.id}/candidates`}
          onClick={(e) => e.stopPropagation()}
          className="text-sm text-blue-600 hover:text-blue-800 font-medium transition-colors focus:outline-none focus-visible:underline"
        >
          View Candidates →
        </Link>
        <Link
          to={`/jobs/${job.id}`}
          onClick={(e) => e.stopPropagation()}
          className="text-sm text-gray-400 hover:text-gray-700 transition-colors focus:outline-none focus-visible:underline"
        >
          Edit
        </Link>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Filter bar field components
// ---------------------------------------------------------------------------
interface TextFilterProps {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
}

function TextFilter({ label, value, onChange, placeholder }: TextFilterProps) {
  return (
    <div className="flex flex-col gap-1 min-w-[140px]">
      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder ?? label}
        className="border border-gray-300 rounded-md px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow bg-white"
      />
    </div>
  )
}

interface SelectFilterProps {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}

function SelectFilter({ label, value, onChange, options }: SelectFilterProps) {
  return (
    <div className="flex flex-col gap-1 min-w-[140px]">
      <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border border-gray-300 rounded-md px-3 py-1.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-shadow bg-white appearance-none cursor-pointer"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function JobsPage() {
  // Raw filter state (text inputs are raw; selects fire immediately)
  const [titleRaw, setTitleRaw] = useState('')
  const [departmentRaw, setDepartmentRaw] = useState('')
  const [locationRaw, setLocationRaw] = useState('')
  const [status, setStatus] = useState('')
  const [employmentType, setEmploymentType] = useState('')
  const [experienceLevel, setExperienceLevel] = useState('')
  const [remoteType, setRemoteType] = useState('')

  // Debounced text values
  const title = useDebounce(titleRaw, 300)
  const department = useDebounce(departmentRaw, 300)
  const location = useDebounce(locationRaw, 300)

  const filters = {
    status: status || undefined,
    title: title || undefined,
    department: department || undefined,
    location: location || undefined,
    employment_type: employmentType || undefined,
    experience_level: experienceLevel || undefined,
    remote_type: remoteType || undefined,
  }

  const {
    data,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['jobs', filters],
    queryFn: ({ pageParam }) =>
      listJobs({ ...filters, cursor: (pageParam as string | null) ?? undefined }),
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    initialPageParam: null as string | null,
  })

  // Flatten pages
  const jobs: JobResponse[] = data?.pages.flatMap((page) => page.data) ?? []

  // Intersection observer for infinite scroll
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

  const hasActiveFilter =
    titleRaw || departmentRaw || locationRaw || status || employmentType || experienceLevel || remoteType

  function clearFilters() {
    setTitleRaw('')
    setDepartmentRaw('')
    setLocationRaw('')
    setStatus('')
    setEmploymentType('')
    setExperienceLevel('')
    setRemoteType('')
  }

  return (
    <div className="max-w-6xl mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Jobs</h1>
        <Link
          to="/jobs/new"
          className="inline-flex items-center gap-1.5 bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New Job
        </Link>
      </div>

      {/* Filter bar */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <SelectFilter
            label="Status"
            value={status}
            onChange={setStatus}
            options={[
              { value: '', label: 'All statuses' },
              { value: 'open', label: 'Open' },
              { value: 'closed', label: 'Closed' },
            ]}
          />
          <TextFilter label="Title" value={titleRaw} onChange={setTitleRaw} placeholder="Search title…" />
          <TextFilter label="Department" value={departmentRaw} onChange={setDepartmentRaw} placeholder="e.g. Engineering" />
          <TextFilter label="Location" value={locationRaw} onChange={setLocationRaw} placeholder="e.g. New York" />
          <SelectFilter
            label="Type"
            value={employmentType}
            onChange={setEmploymentType}
            options={[
              { value: '', label: 'All types' },
              { value: 'full_time', label: 'Full-time' },
              { value: 'part_time', label: 'Part-time' },
              { value: 'contract', label: 'Contract' },
              { value: 'internship', label: 'Internship' },
            ]}
          />
          <SelectFilter
            label="Level"
            value={experienceLevel}
            onChange={setExperienceLevel}
            options={[
              { value: '', label: 'All levels' },
              { value: 'entry', label: 'Entry' },
              { value: 'mid', label: 'Mid' },
              { value: 'senior', label: 'Senior' },
              { value: 'lead', label: 'Lead' },
              { value: 'executive', label: 'Executive' },
            ]}
          />
          <SelectFilter
            label="Remote"
            value={remoteType}
            onChange={setRemoteType}
            options={[
              { value: '', label: 'All' },
              { value: 'remote', label: 'Remote' },
              { value: 'hybrid', label: 'Hybrid' },
              { value: 'onsite', label: 'On-site' },
            ]}
          />
          {hasActiveFilter && (
            <div className="flex flex-col justify-end">
              <button
                type="button"
                onClick={clearFilters}
                className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-800 border border-gray-200 rounded-md hover:border-gray-300 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Error state */}
      {isError && (
        <div className="text-center py-16">
          <p className="text-red-600 font-medium mb-2">Failed to load jobs</p>
          <p className="text-sm text-gray-500">Check your connection and try refreshing the page.</p>
        </div>
      )}

      {/* Loading skeletons (first load only) */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && jobs.length === 0 && (
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
              d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
            />
          </svg>
          <p className="text-gray-500 text-lg font-medium mb-1">
            {hasActiveFilter ? 'No jobs match your filters' : 'No jobs yet'}
          </p>
          <p className="text-gray-400 text-sm mb-6">
            {hasActiveFilter
              ? 'Try adjusting or clearing your filters.'
              : 'Get started by creating your first job opening.'}
          </p>
          {!hasActiveFilter && (
            <Link
              to="/jobs/new"
              className="inline-flex items-center gap-1.5 bg-blue-600 text-white px-5 py-2.5 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Create your first job
            </Link>
          )}
          {hasActiveFilter && (
            <button
              type="button"
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:underline focus:outline-none"
            >
              Clear all filters
            </button>
          )}
        </div>
      )}

      {/* Job grid */}
      {!isLoading && !isError && jobs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      )}

      {/* Load-more skeletons while fetching next page */}
      {isFetchingNextPage && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {/* Infinite scroll sentinel */}
      <div ref={sentinelRef} className="h-1" aria-hidden="true" />
    </div>
  )
}
