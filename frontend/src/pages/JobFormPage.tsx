import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useForm, Controller, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { jobsApi } from '../api/jobs'
import type { EmploymentType, ExperienceLevel, RemoteType } from '../types'

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const schema = z
  .object({
    title: z.string().min(1, 'Title is required').max(200, 'Title must be 200 characters or less'),
    description: z.string().min(1, 'Description is required'),
    department: z.string().max(100, 'Department must be 100 characters or less').optional().or(z.literal('')),
    location: z.string().max(100, 'Location must be 100 characters or less').optional().or(z.literal('')),
    salary_min: z.preprocess(
      (v) => (v === '' || v === null || v === undefined) ? undefined : Number(v),
      z.number({ message: 'Must be a number' }).positive('Must be a positive number').int('Must be a whole number').optional()
    ),
    salary_max: z.preprocess(
      (v) => (v === '' || v === null || v === undefined) ? undefined : Number(v),
      z.number({ message: 'Must be a number' }).positive('Must be a positive number').int('Must be a whole number').optional()
    ),
    required_skills: z.array(z.string()),
    employment_type: z
      .enum(['full_time', 'part_time', 'contract', 'internship', ''] as const)
      .optional(),
    experience_level: z
      .enum(['junior', 'mid', 'senior', 'lead', ''] as const)
      .optional(),
    remote_type: z.enum(['onsite', 'remote', 'hybrid', ''] as const).optional(),
  })
  .refine(
    (data) => {
      const min = Number(data.salary_min)
      const max = Number(data.salary_max)
      if (data.salary_min && data.salary_max && min > 0 && max > 0) {
        return max >= min
      }
      return true
    },
    { message: 'Salary max must be greater than or equal to salary min', path: ['salary_max'] },
  )

type FormData = z.infer<typeof schema>

// ---------------------------------------------------------------------------
// Tag Input component
// ---------------------------------------------------------------------------

interface TagInputProps {
  value: string[]
  onChange: (tags: string[]) => void
  hasError?: boolean
}

function TagInput({ value, onChange, hasError }: TagInputProps) {
  const [inputVal, setInputVal] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const addTag = (raw: string) => {
    const tag = raw.trim()
    if (!tag || value.includes(tag) || value.length >= 30) return
    onChange([...value, tag])
    setInputVal('')
  }

  const removeTag = (index: number) => {
    onChange(value.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addTag(inputVal)
    } else if (e.key === 'Backspace' && inputVal === '' && value.length > 0) {
      removeTag(value.length - 1)
    }
  }

  const handleBlur = () => {
    if (inputVal.trim()) addTag(inputVal)
  }

  return (
    <div
      className={`flex flex-wrap gap-1.5 min-h-[42px] w-full border rounded-md px-3 py-2 bg-white cursor-text transition-colors focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 ${
        hasError ? 'border-red-400' : 'border-gray-300'
      }`}
      onClick={() => inputRef.current?.focus()}
    >
      {value.map((tag, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 border border-blue-200 text-sm px-2 py-0.5 rounded"
        >
          {tag}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              removeTag(i)
            }}
            className="text-blue-400 hover:text-blue-700 leading-none focus:outline-none"
            aria-label={`Remove ${tag}`}
          >
            ×
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        value={inputVal}
        onChange={(e) => setInputVal(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={value.length === 0 ? 'Type a skill and press Enter or comma' : ''}
        className="flex-1 min-w-[140px] outline-none text-sm bg-transparent placeholder-gray-400"
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fieldClass =
  'w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
const labelClass = 'block text-sm font-medium text-gray-700 mb-1'
const errorClass = 'mt-1 text-xs text-red-600'

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className={errorClass}>{message}</p>
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function JobFormPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const isEdit = Boolean(jobId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  // Fetch existing job in edit mode
  const {
    data: job,
    isLoading: jobLoading,
    isError: jobError,
  } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsApi.get(jobId!),
    enabled: isEdit,
  })

  const {
    register,
    handleSubmit,
    reset,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema) as Resolver<FormData>,
    defaultValues: { required_skills: [] },
  })

  // Pre-fill form when job data arrives
  useEffect(() => {
    if (job) {
      reset({
        title: job.title,
        description: job.description,
        department: job.department ?? '',
        location: job.location ?? '',
        salary_min: job.salary_min ?? undefined,
        salary_max: job.salary_max ?? undefined,
        required_skills: job.required_skills ?? [],
        employment_type: (job.employment_type ?? '') as EmploymentType | '',
        experience_level: (job.experience_level ?? '') as ExperienceLevel | '',
        remote_type: (job.remote_type ?? '') as RemoteType | '',
      })
    }
  }, [job, reset])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: FormData) =>
      jobsApi.create({
        title: data.title,
        description: data.description,
        department: data.department || undefined,
        location: data.location || undefined,
        salary_min: data.salary_min ? Number(data.salary_min) : undefined,
        salary_max: data.salary_max ? Number(data.salary_max) : undefined,
        required_skills: data.required_skills,
        employment_type: (data.employment_type || undefined) as EmploymentType | undefined,
        experience_level: (data.experience_level || undefined) as ExperienceLevel | undefined,
        remote_type: (data.remote_type || undefined) as RemoteType | undefined,
      }),
    onSuccess: (newJob) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      toast.success('Job created')
      navigate('/jobs/' + newJob.id)
    },
    onError: () => toast.error('Failed to create job'),
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: FormData) =>
      jobsApi.update(jobId!, {
        title: data.title,
        description: data.description,
        department: data.department || undefined,
        location: data.location || undefined,
        salary_min: data.salary_min ? Number(data.salary_min) : undefined,
        salary_max: data.salary_max ? Number(data.salary_max) : undefined,
        required_skills: data.required_skills,
        employment_type: (data.employment_type || undefined) as EmploymentType | undefined,
        experience_level: (data.experience_level || undefined) as ExperienceLevel | undefined,
        remote_type: (data.remote_type || undefined) as RemoteType | undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['job', jobId] })
      toast.success('Job updated')
    },
    onError: () => toast.error('Failed to update job'),
  })

  // Close job mutation
  const closeMutation = useMutation({
    mutationFn: () => jobsApi.close(jobId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      queryClient.invalidateQueries({ queryKey: ['job', jobId] })
      toast.success('Job closed')
    },
    onError: () => toast.error('Failed to close job'),
  })

  const onSubmit = (data: FormData) => {
    if (isEdit) {
      updateMutation.mutate(data)
    } else {
      createMutation.mutate(data)
    }
  }

  const isPending =
    isSubmitting || createMutation.isPending || updateMutation.isPending

  // -------------------------------------------------------------------------
  // Loading / error states for edit mode fetch
  // -------------------------------------------------------------------------

  if (isEdit && jobLoading) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4">
        <div className="flex justify-center py-24">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
        </div>
      </div>
    )
  }

  if (isEdit && jobError) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4">
        <p className="text-red-600 text-center py-12">Failed to load job. Please try again.</p>
      </div>
    )
  }

  const pageTitle = isEdit ? (job?.title ?? 'Edit Job') : 'New Job'
  const jobIsClosed = isEdit && job?.status === 'closed'

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6 gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <Link
            to="/jobs"
            className="flex-shrink-0 flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800 transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Jobs
          </Link>
          <span className="text-gray-300 select-none">/</span>
          <h1 className="text-xl font-semibold text-gray-900 truncate">{pageTitle}</h1>
          {isEdit && (
            <span
              className={`flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${
                jobIsClosed
                  ? 'bg-gray-100 text-gray-600'
                  : 'bg-green-100 text-green-700'
              }`}
            >
              {job?.status}
            </span>
          )}
        </div>

        {isEdit && (
          <div className="flex items-center gap-2 flex-shrink-0">
            <Link
              to={`/jobs/${jobId}/candidates`}
              className="text-sm text-blue-600 border border-blue-200 px-3 py-1.5 rounded-md hover:bg-blue-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              View Candidates
            </Link>
            {!jobIsClosed && (
              <button
                type="button"
                onClick={() => {
                  if (window.confirm('Close this job opening? Candidates will no longer be able to apply.')) {
                    closeMutation.mutate()
                  }
                }}
                disabled={closeMutation.isPending}
                className="text-sm text-red-600 border border-red-300 px-3 py-1.5 rounded-md hover:bg-red-50 disabled:opacity-50 transition-colors"
              >
                {closeMutation.isPending ? 'Closing…' : 'Close Job'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">

          {/* Section: Basic info */}
          <div className="p-6 space-y-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Basic Information
            </p>

            {/* Title */}
            <div>
              <label className={labelClass}>
                Job Title <span className="text-red-500">*</span>
              </label>
              <input
                {...register('title')}
                className={`${fieldClass} ${errors.title ? 'border-red-400 focus:ring-red-400' : ''}`}
                placeholder="e.g. Senior Frontend Engineer"
              />
              <FieldError message={errors.title?.message} />
            </div>

            {/* Description */}
            <div>
              <label className={labelClass}>
                Description <span className="text-red-500">*</span>
              </label>
              <textarea
                {...register('description')}
                rows={7}
                className={`${fieldClass} resize-y ${errors.description ? 'border-red-400 focus:ring-red-400' : ''}`}
                placeholder="Describe responsibilities, requirements, and what makes this role great…"
              />
              <FieldError message={errors.description?.message} />
            </div>

            {/* Department + Location */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Department</label>
                <input
                  {...register('department')}
                  className={fieldClass}
                  placeholder="e.g. Engineering"
                />
              </div>
              <div>
                <label className={labelClass}>Location</label>
                <input
                  {...register('location')}
                  className={fieldClass}
                  placeholder="e.g. New York, NY"
                />
              </div>
            </div>
          </div>

          {/* Section: Compensation */}
          <div className="p-6 space-y-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Compensation
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className={labelClass}>Salary Min</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm select-none">
                    $
                  </span>
                  <input
                    {...register('salary_min')}
                    type="number"
                    min={0}
                    className={`${fieldClass} pl-6 ${errors.salary_min ? 'border-red-400 focus:ring-red-400' : ''}`}
                    placeholder="80000"
                  />
                </div>
                <FieldError message={errors.salary_min?.message} />
              </div>
              <div>
                <label className={labelClass}>Salary Max</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm select-none">
                    $
                  </span>
                  <input
                    {...register('salary_max')}
                    type="number"
                    min={0}
                    className={`${fieldClass} pl-6 ${errors.salary_max ? 'border-red-400 focus:ring-red-400' : ''}`}
                    placeholder="120000"
                  />
                </div>
                <FieldError message={errors.salary_max?.message} />
              </div>
            </div>
          </div>

          {/* Section: Details */}
          <div className="p-6 space-y-5">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Role Details
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className={labelClass}>Employment Type</label>
                <select {...register('employment_type')} className={fieldClass}>
                  <option value="">Any</option>
                  <option value="full_time">Full Time</option>
                  <option value="part_time">Part Time</option>
                  <option value="contract">Contract</option>
                  <option value="internship">Internship</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Experience Level</label>
                <select {...register('experience_level')} className={fieldClass}>
                  <option value="">Any</option>
                  <option value="junior">Junior</option>
                  <option value="mid">Mid</option>
                  <option value="senior">Senior</option>
                  <option value="lead">Lead</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>Remote Policy</label>
                <select {...register('remote_type')} className={fieldClass}>
                  <option value="">Any</option>
                  <option value="onsite">Onsite</option>
                  <option value="remote">Remote</option>
                  <option value="hybrid">Hybrid</option>
                </select>
              </div>
            </div>

            {/* Skills tag input */}
            <div>
              <label className={labelClass}>Required Skills</label>
              <Controller
                name="required_skills"
                control={control}
                render={({ field }) => (
                  <TagInput
                    value={field.value}
                    onChange={field.onChange}
                    hasError={Boolean(errors.required_skills)}
                  />
                )}
              />
              <p className="mt-1 text-xs text-gray-400">
                Press Enter or comma to add · Backspace to remove last · max 30
              </p>
            </div>
          </div>

          {/* Footer actions */}
          <div className="px-6 py-4 bg-gray-50 rounded-b-lg flex items-center gap-3">
            <button
              type="submit"
              disabled={isPending}
              className="bg-blue-600 text-white px-5 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {isPending
                ? isEdit
                  ? 'Saving…'
                  : 'Creating…'
                : isEdit
                ? 'Save Changes'
                : 'Create Job'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/jobs')}
              className="text-sm text-gray-600 px-4 py-2 rounded-md hover:bg-gray-200 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
            >
              Cancel
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
