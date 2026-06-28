import api from './client'
import type {
  CandidateCreate,
  CandidateDetailResponse,
  ApplicationResponse,
  ResumeUploadResponse,
  RescoreResponse,
} from '../types'

// ---------------------------------------------------------------------------
// Named function exports (spec-required interface)
// ---------------------------------------------------------------------------
export function createCandidate(data: CandidateCreate): Promise<CandidateDetailResponse> {
  return api.post<CandidateDetailResponse>('/candidates', data).then((r) => r.data)
}

export function getCandidate(id: string): Promise<CandidateDetailResponse> {
  return api.get<CandidateDetailResponse>(`/candidates/${id}`).then((r) => r.data)
}

export function deleteCandidate(id: string): Promise<void> {
  return api.delete(`/candidates/${id}`).then(() => undefined)
}

export function createApplication(candidateId: string, jobId: string): Promise<ApplicationResponse> {
  return api
    .post<ApplicationResponse>(`/candidates/${candidateId}/applications`, { job_id: jobId })
    .then((r) => r.data)
}

export function updateApplicationStatus(applicationId: string, status: string): Promise<ApplicationResponse> {
  return api
    .patch<ApplicationResponse>(`/applications/${applicationId}/status`, { status })
    .then((r) => r.data)
}

export function uploadResume(
  candidateId: string,
  applicationId: string,
  file: File
): Promise<ResumeUploadResponse> {
  const form = new FormData()
  form.append('file', file)
  return api
    .post<ResumeUploadResponse>(
      `/candidates/${candidateId}/applications/${applicationId}/resume`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    .then((r) => r.data)
}

export function rescore(candidateId: string, applicationId: string): Promise<RescoreResponse> {
  return api
    .post<RescoreResponse>(`/candidates/${candidateId}/applications/${applicationId}/rescore`)
    .then((r) => r.data)
}

export const candidatesApi = {
  create: (body: CandidateCreate) =>
    api.post<CandidateDetailResponse>('/candidates', body).then((r) => r.data),

  get: (id: string) =>
    api.get<CandidateDetailResponse>(`/candidates/${id}`).then((r) => r.data),

  delete: (id: string) => api.delete(`/candidates/${id}`),

  addApplication: (candidateId: string, jobId: string) =>
    api
      .post<ApplicationResponse>(`/candidates/${candidateId}/applications`, { job_id: jobId })
      .then((r) => r.data),

  uploadResume: (candidateId: string, appId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api
      .post<ResumeUploadResponse>(
        `/candidates/${candidateId}/applications/${appId}/resume`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      )
      .then((r) => r.data)
  },

  rescore: (candidateId: string, appId: string) =>
    api
      .post<RescoreResponse>(`/candidates/${candidateId}/applications/${appId}/rescore`)
      .then((r) => r.data),
}

export const applicationsApi = {
  updateStatus: (appId: string, status: string) =>
    api
      .patch<ApplicationResponse>(`/applications/${appId}/status`, { status })
      .then((r) => r.data),
}
