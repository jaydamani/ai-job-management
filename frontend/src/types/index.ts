export interface RecruiterResponse {
  id: string
  email: string
  name: string | null
  created_at: string
  updated_at: string
}

export type JobStatus = 'open' | 'closed'
export type EmploymentType = 'full_time' | 'part_time' | 'contract' | 'internship'
export type ExperienceLevel = 'entry' | 'mid' | 'senior' | 'lead' | 'executive'
export type RemoteType = 'onsite' | 'remote' | 'hybrid'
export type PipelineStatus = 'applied' | 'screened' | 'interviewed' | 'rejected' | 'hired'

export interface JobResponse {
  id: string
  recruiter_id: string
  title: string
  description: string
  department?: string
  location?: string
  salary_min?: number
  salary_max?: number
  required_skills: string[]
  employment_type?: EmploymentType
  experience_level?: ExperienceLevel
  remote_type?: RemoteType
  status: JobStatus
  created_at: string
  updated_at: string
}

export interface JobCreate {
  title: string
  description: string
  department?: string
  location?: string
  salary_min?: number
  salary_max?: number
  required_skills?: string[]
  employment_type?: EmploymentType
  experience_level?: ExperienceLevel
  remote_type?: RemoteType
}

export interface JobUpdate {
  title?: string
  description?: string
  department?: string
  location?: string
  salary_min?: number
  salary_max?: number
  required_skills?: string[]
  employment_type?: EmploymentType
  experience_level?: ExperienceLevel
  remote_type?: RemoteType
}

export interface CandidateResponse {
  id: string
  name: string
  email: string
  phone?: string
  location_preference?: string
  linkedin_url?: string
  portfolio_url?: string
  github_url?: string
  created_at: string
}

export interface CandidateCreate {
  name: string
  email: string
  phone?: string
  location_preference?: string
  linkedin_url?: string
  portfolio_url?: string
  github_url?: string
  expected_salary_min?: number
  expected_salary_max?: number
  notice_period_days?: number
  source?: string
  notes?: string
  job_id: string
}

export interface ApplicationSummaryResponse {
  id: string
  job_id: string
  job_title?: string
  status: PipelineStatus
  fit_score?: number
  fit_explanation?: string
  resume_url?: string
  applied_at: string
  updated_at: string
}

export interface CandidateDetailResponse {
  id: string
  recruiter_id: string
  name: string
  email: string
  phone?: string
  location_preference?: string
  linkedin_url?: string
  portfolio_url?: string
  github_url?: string
  expected_salary_min?: number
  expected_salary_max?: number
  notice_period_days?: number
  source?: string
  notes?: string
  created_at: string
  updated_at: string
  applications: ApplicationSummaryResponse[]
}

export interface ApplicationInCandidateList {
  id: string
  job_id: string
  job_title?: string
  status: PipelineStatus
  fit_score?: number
  fit_explanation?: string
  strengths?: string[]
  gaps?: string[]
  ai_parsed_resume?: string
  ai_status?: string
  resume_url?: string
  applied_at: string
}

export interface CandidateWithApplicationResponse {
  id: string
  name: string
  email: string
  phone?: string
  location_preference?: string
  linkedin_url?: string
  portfolio_url?: string
  github_url?: string
  created_at: string
  application: ApplicationInCandidateList
}

export interface ApplicationResponse {
  id: string
  candidate_id: string
  job_id: string
  status: PipelineStatus
  fit_score?: number
  fit_explanation?: string
  ai_parsed_resume?: string
  interview_notes?: string
  strengths?: string[]
  gaps?: string[]
  ai_status?: string
  resume_url?: string
  applied_at: string
  updated_at: string
}

export interface ResumeUploadResponse {
  resume_url: string
  ai_status: string
  ai_parsed_resume?: string
  fit_score?: number
  fit_explanation?: string
  strengths?: string[]
  gaps?: string[]
}

export interface RescoreResponse {
  ai_status: string
  ai_parsed_resume?: string
  fit_score?: number
  fit_explanation?: string
  strengths?: string[]
  gaps?: string[]
}

export interface PaginatedResponse<T> {
  data: T[]
  next_cursor: string | null
  has_more: boolean
}
