import { useState, useRef } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useForm, type Resolver } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { getJob } from '../api/jobs'
import { createCandidate, uploadResume } from '../api/candidates'

// ---------------------------------------------------------------------------
// Schema
// ---------------------------------------------------------------------------

const schema = z
  .object({
    name: z.string().min(1, 'Name is required'),
    email: z.string().email('Enter a valid email address'),
    phone: z.string().optional().or(z.literal('')),
    location_preference: z.string().optional().or(z.literal('')),
    linkedin_url: z
      .string()
      .url('Enter a valid URL (e.g. https://linkedin.com/in/…)')
      .optional()
      .or(z.literal('')),
    portfolio_url: z
      .string()
      .url('Enter a valid URL')
      .optional()
      .or(z.literal('')),
    github_url: z
      .string()
      .url('Enter a valid URL (e.g. https://github.com/…)')
      .optional()
      .or(z.literal('')),
    expected_salary_min: z.preprocess(
      (v) => (v === '' || v === null || v === undefined) ? undefined : Number(v),
      z.number({ message: 'Must be a number' }).positive('Must be a positive number').int('Must be a whole number').optional()
    ),
    expected_salary_max: z.preprocess(
      (v) => (v === '' || v === null || v === undefined) ? undefined : Number(v),
      z.number({ message: 'Must be a number' }).positive('Must be a positive number').int('Must be a whole number').optional()
    ),
    notice_period_days: z.preprocess(
      (v) => (v === '' || v === null || v === undefined) ? undefined : Number(v),
      z.number({ message: 'Must be a number' }).nonnegative('Must be 0 or more').int('Must be a whole number').optional()
    ),
    source: z.string().optional().or(z.literal('')),
    notes: z.string().optional().or(z.literal('')),
  })
  .refine(
    (data) => {
      const min = Number(data.expected_salary_min)
      const max = Number(data.expected_salary_max)
      if (data.expected_salary_min && data.expected_salary_max && min > 0 && max > 0) {
        return max >= min
      }
      return true
    },
    {
      message: 'Max must be greater than or equal to min',
      path: ['expected_salary_max'],
    },
  )

type FormData = z.infer<typeof schema>

// ---------------------------------------------------------------------------
// Shared style helpers (matches existing codebase conventions)
// ---------------------------------------------------------------------------

const fieldClass =
  'w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors'
const fieldErrorClass =
  'w-full border border-red-400 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-red-400 transition-colors'
const labelClass = 'block text-sm font-medium text-gray-700 mb-1'
const errorClass = 'mt-1 text-xs text-red-600'

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className={errorClass}>{message}</p>
}

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

function StepIndicator({ step }: { step: 1 | 2 }) {
  return (
    <div className="flex items-center gap-2 mb-6" aria-label="Progress">
      {/* Step 1 */}
      <div
        className={`flex items-center gap-1.5 text-sm font-medium ${
          step === 1 ? 'text-blue-600' : 'text-gray-400'
        }`}
      >
        <span
          className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-semibold ${
            step === 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
          }`}
        >
          {step > 1 ? (
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            '1'
          )}
        </span>
        Resume
      </div>

      {/* Connector */}
      <div className="flex-1 h-px bg-gray-200 mx-1" aria-hidden="true" />

      {/* Step 2 */}
      <div
        className={`flex items-center gap-1.5 text-sm font-medium ${
          step === 2 ? 'text-blue-600' : 'text-gray-400'
        }`}
      >
        <span
          className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-xs font-semibold ${
            step === 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
          }`}
        >
          2
        </span>
        Details
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 1: Resume upload
// ---------------------------------------------------------------------------

interface Step1Props {
  file: File | null
  onFileChange: (file: File | null) => void
  onContinue: () => void
}

function Step1({ file, onFileChange, onContinue }: Step1Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [fileError, setFileError] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null
    if (!selected) return
    if (selected.size > 5 * 1024 * 1024) {
      setFileError('File must be under 5 MB')
      e.target.value = ''
      return
    }
    setFileError(null)
    onFileChange(selected)
  }

  const handleRemove = () => {
    onFileChange(null)
    setFileError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">
      <div className="p-6 space-y-4">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
          Resume (optional)
        </p>
        <p className="text-sm text-gray-500">
          Upload a PDF resume and Gappeo will use AI to parse it and score the candidate against the
          job requirements. You can always add or retry from the candidate page later.
        </p>

        {/* Drop area / file selector */}
        {!file ? (
          <div>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="inline-flex items-center gap-2 border border-dashed border-gray-300 rounded-lg px-5 py-4 w-full justify-center text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              <svg
                className="w-5 h-5 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.338-2.32 5.75 5.75 0 011.07 11.095"
                />
              </svg>
              Choose PDF file
            </button>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              className="sr-only"
              aria-label="Upload resume PDF"
            />
            {fileError && <p className={`${errorClass} mt-2`}>{fileError}</p>}
          </div>
        ) : (
          <div className="flex items-center gap-3 border border-green-200 bg-green-50 rounded-lg px-4 py-3">
            <svg
              className="w-5 h-5 text-green-600 flex-shrink-0"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            </svg>
            <span className="flex-1 min-w-0 text-sm text-green-800 font-medium truncate">
              {file.name}
            </span>
            <span className="text-xs text-green-600 flex-shrink-0 tabular-nums">
              {(file.size / 1024).toFixed(0)} KB
            </span>
            <button
              type="button"
              onClick={handleRemove}
              className="text-green-500 hover:text-red-500 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 rounded"
              aria-label="Remove file"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Footer actions */}
      <div className="px-6 py-4 bg-gray-50 rounded-b-lg flex items-center gap-3">
        <button
          type="button"
          onClick={onContinue}
          className="bg-blue-600 text-white px-5 py-2 rounded-md text-sm font-medium hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Continue &rarr;
        </button>
        {!file && (
          <button
            type="button"
            onClick={onContinue}
            className="text-sm text-gray-500 hover:text-gray-700 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 rounded px-1"
          >
            Skip
          </button>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 2: Candidate form
// ---------------------------------------------------------------------------

interface Step2Props {
  jobId: string
  file: File | null
  onBack: () => void
}

function Step2({ jobId, file, onBack }: Step2Props) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) as Resolver<FormData> })

  const onSubmit = async (data: FormData) => {
    setSubmitting(true)
    setSubmitError(null)

    let candidateId: string
    let applicationId: string

    try {
      const candidate = await createCandidate({
        name: data.name,
        email: data.email,
        phone: data.phone || undefined,
        location_preference: data.location_preference || undefined,
        linkedin_url: data.linkedin_url || undefined,
        portfolio_url: data.portfolio_url || undefined,
        github_url: data.github_url || undefined,
        expected_salary_min: data.expected_salary_min
          ? Number(data.expected_salary_min)
          : undefined,
        expected_salary_max: data.expected_salary_max
          ? Number(data.expected_salary_max)
          : undefined,
        notice_period_days: data.notice_period_days
          ? Number(data.notice_period_days)
          : undefined,
        source: data.source || undefined,
        notes: data.notes || undefined,
        job_id: jobId,
      })
      candidateId = candidate.id
      applicationId = candidate.applications[0]?.id
    } catch {
      setSubmitError('Failed to save candidate. Please try again.')
      setSubmitting(false)
      return
    }

    // Step 3 (optional): upload resume
    if (file) {
      const toastId = toast.loading('Parsing resume with AI…')
      try {
        const result = await uploadResume(candidateId, applicationId, file)
        toast.dismiss(toastId)
        if (result.ai_status === 'failed') {
          toast.error('AI parsing failed — you can retry from the candidate page')
        }
      } catch {
        toast.dismiss(toastId)
        toast.error('Resume upload failed — you can retry from the candidate page')
      }
    }

    queryClient.invalidateQueries({ queryKey: ['candidates', jobId] })
    navigate(`/jobs/${jobId}/candidates/${candidateId}`)
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-100">

        {/* Section: Required info */}
        <div className="p-6 space-y-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Basic Information
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>
                Name <span className="text-red-500">*</span>
              </label>
              <input
                {...register('name')}
                className={errors.name ? fieldErrorClass : fieldClass}
                placeholder="Jane Smith"
                autoFocus
              />
              <FieldError message={errors.name?.message} />
            </div>
            <div>
              <label className={labelClass}>
                Email <span className="text-red-500">*</span>
              </label>
              <input
                {...register('email')}
                type="email"
                className={errors.email ? fieldErrorClass : fieldClass}
                placeholder="jane@example.com"
              />
              <FieldError message={errors.email?.message} />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Phone</label>
              <input
                {...register('phone')}
                type="tel"
                className={fieldClass}
                placeholder="+1 (555) 000-0000"
              />
            </div>
            <div>
              <label className={labelClass}>Location Preference</label>
              <input
                {...register('location_preference')}
                className={fieldClass}
                placeholder="e.g. Remote, New York"
              />
            </div>
          </div>
        </div>

        {/* Section: Online presence */}
        <div className="p-6 space-y-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Online Profiles
          </p>

          <div>
            <label className={labelClass}>LinkedIn</label>
            <input
              {...register('linkedin_url')}
              className={errors.linkedin_url ? fieldErrorClass : fieldClass}
              placeholder="https://linkedin.com/in/…"
            />
            <FieldError message={errors.linkedin_url?.message} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={labelClass}>Portfolio</label>
              <input
                {...register('portfolio_url')}
                className={errors.portfolio_url ? fieldErrorClass : fieldClass}
                placeholder="https://…"
              />
              <FieldError message={errors.portfolio_url?.message} />
            </div>
            <div>
              <label className={labelClass}>GitHub</label>
              <input
                {...register('github_url')}
                className={errors.github_url ? fieldErrorClass : fieldClass}
                placeholder="https://github.com/…"
              />
              <FieldError message={errors.github_url?.message} />
            </div>
          </div>
        </div>

        {/* Section: Compensation + availability */}
        <div className="p-6 space-y-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Compensation & Availability
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className={labelClass}>Expected Salary Min</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm select-none">
                  $
                </span>
                <input
                  {...register('expected_salary_min')}
                  type="number"
                  min={0}
                  className={`${errors.expected_salary_min ? fieldErrorClass : fieldClass} pl-6`}
                  placeholder="80000"
                />
              </div>
              <FieldError message={errors.expected_salary_min?.message} />
            </div>
            <div>
              <label className={labelClass}>Expected Salary Max</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm select-none">
                  $
                </span>
                <input
                  {...register('expected_salary_max')}
                  type="number"
                  min={0}
                  className={`${errors.expected_salary_max ? fieldErrorClass : fieldClass} pl-6`}
                  placeholder="120000"
                />
              </div>
              <FieldError message={errors.expected_salary_max?.message} />
            </div>
            <div>
              <label className={labelClass}>Notice Period (days)</label>
              <input
                {...register('notice_period_days')}
                type="number"
                min={0}
                className={errors.notice_period_days ? fieldErrorClass : fieldClass}
                placeholder="30"
              />
              <FieldError message={errors.notice_period_days?.message} />
            </div>
          </div>
        </div>

        {/* Section: Additional context */}
        <div className="p-6 space-y-5">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
            Additional Context
          </p>

          <div>
            <label className={labelClass}>Source</label>
            <input
              {...register('source')}
              className={fieldClass}
              placeholder="e.g. LinkedIn, Referral, Job board"
            />
          </div>

          <div>
            <label className={labelClass}>Notes</label>
            <textarea
              {...register('notes')}
              rows={4}
              className={`${fieldClass} resize-y`}
              placeholder="Any internal notes about this candidate…"
            />
          </div>
        </div>

        {/* Submit error banner */}
        {submitError && (
          <div className="px-6 py-3 bg-red-50 border-t border-red-100">
            <p className="text-sm text-red-700">{submitError}</p>
          </div>
        )}

        {/* Footer actions */}
        <div className="px-6 py-4 bg-gray-50 rounded-b-lg flex items-center gap-3">
          <button
            type="submit"
            disabled={submitting}
            className="bg-blue-600 text-white px-5 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            {submitting ? 'Saving…' : file ? 'Add Candidate & Upload Resume' : 'Add Candidate'}
          </button>
          <button
            type="button"
            onClick={onBack}
            disabled={submitting}
            className="text-sm text-gray-600 px-4 py-2 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2"
          >
            &larr; Back
          </button>
        </div>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function AddCandidatePage() {
  const { jobId } = useParams<{ jobId: string }>()
  const [step, setStep] = useState<1 | 2>(1)
  const [file, setFile] = useState<File | null>(null)

  const { data: job } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => getJob(jobId!),
    enabled: Boolean(jobId),
  })

  const jobTitle = job?.title ?? '…'

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      {/* Breadcrumb */}
      <nav
        className="flex items-center gap-1.5 text-sm text-gray-400 mb-6"
        aria-label="Breadcrumb"
      >
        <Link to="/jobs" className="hover:text-blue-600 transition-colors">
          Jobs
        </Link>
        <svg
          className="w-3 h-3 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <Link
          to={`/jobs/${jobId}/candidates`}
          className="hover:text-blue-600 transition-colors truncate max-w-[200px]"
          title={jobTitle !== '…' ? jobTitle : undefined}
        >
          {jobTitle}
        </Link>
        <svg
          className="w-3 h-3 flex-shrink-0"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden="true"
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-gray-500">Add Candidate</span>
      </nav>

      {/* Page heading */}
      <div className="flex items-center justify-between mb-6 gap-4">
        <h1 className="text-xl font-semibold text-gray-900">
          {step === 1 ? 'Step 1 of 2: Resume' : 'Step 2 of 2: Candidate Details'}
        </h1>
      </div>

      {/* Step indicator */}
      <StepIndicator step={step} />

      {/* Step panels */}
      {step === 1 ? (
        <Step1
          file={file}
          onFileChange={setFile}
          onContinue={() => setStep(2)}
        />
      ) : (
        <Step2
          jobId={jobId!}
          file={file}
          onBack={() => setStep(1)}
        />
      )}
    </div>
  )
}
