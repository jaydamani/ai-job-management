import api from './client'
import type {
  JobResponse,
  JobCreate,
  JobUpdate,
  PaginatedResponse,
  CandidateWithApplicationResponse,
} from '../types'

export interface JobsQuery {
  cursor?: string
  limit?: number
  status?: string
  title?: string
  department?: string
  location?: string
  employment_type?: string
  experience_level?: string
  remote_type?: string
}

export const jobsApi = {
  list: (params?: JobsQuery) =>
    api.get<PaginatedResponse<JobResponse>>('/jobs', { params }).then((r) => r.data),

  get: (id: string) =>
    api.get<JobResponse>(`/jobs/${id}`).then((r) => r.data),

  create: (body: JobCreate) =>
    api.post<JobResponse>('/jobs', body).then((r) => r.data),

  update: (id: string, body: JobUpdate) =>
    api.put<JobResponse>(`/jobs/${id}`, body).then((r) => r.data),

  close: (id: string) =>
    api.patch<JobResponse>(`/jobs/${id}/close`).then((r) => r.data),

  getCandidates: (jobId: string, params?: { cursor?: string; limit?: number }) =>
    api
      .get<PaginatedResponse<CandidateWithApplicationResponse>>(`/jobs/${jobId}/candidates`, {
        params,
      })
      .then((r) => r.data),
}

// Named exports for direct import usage
export function listJobs(params?: JobsQuery): Promise<PaginatedResponse<JobResponse>> {
  const cleanParams = params
    ? Object.fromEntries(
        Object.entries(params).filter(([, v]) => v !== undefined && v !== '' && v !== null)
      )
    : undefined
  return api.get<PaginatedResponse<JobResponse>>('/jobs', { params: cleanParams }).then((r) => r.data)
}

export function getJob(id: string): Promise<JobResponse> {
  return api.get<JobResponse>(`/jobs/${id}`).then((r) => r.data)
}

export function createJob(data: JobCreate): Promise<JobResponse> {
  return api.post<JobResponse>('/jobs', data).then((r) => r.data)
}

export function updateJob(id: string, data: Partial<JobCreate>): Promise<JobResponse> {
  return api.put<JobResponse>(`/jobs/${id}`, data).then((r) => r.data)
}

export function closeJob(id: string): Promise<{ id: string; status: string; updated_at: string }> {
  return api.patch<{ id: string; status: string; updated_at: string }>(`/jobs/${id}/close`).then((r) => r.data)
}

export function listJobCandidates(
  jobId: string,
  cursor?: string
): Promise<PaginatedResponse<CandidateWithApplicationResponse>> {
  return api
    .get<PaginatedResponse<CandidateWithApplicationResponse>>(`/jobs/${jobId}/candidates`, {
      params: cursor ? { cursor } : undefined,
    })
    .then((r) => r.data)
}
