import { http, HttpResponse } from 'msw'
import type { RecruiterResponse, JobResponse, PaginatedResponse } from '../../types'

export const mockRecruiter: RecruiterResponse = {
  id: 'recruiter-1',
  email: 'test@example.com',
  name: 'Test Recruiter',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const mockJob: JobResponse = {
  id: 'job-1',
  recruiter_id: 'recruiter-1',
  title: 'Senior Frontend Engineer',
  description: 'Build great UI with React',
  department: 'Engineering',
  location: 'New York, NY',
  required_skills: ['React', 'TypeScript'],
  status: 'open',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const mockJob2: JobResponse = {
  id: 'job-2',
  recruiter_id: 'recruiter-1',
  title: 'Backend Engineer',
  description: 'Build APIs with FastAPI',
  department: 'Engineering',
  required_skills: ['Python', 'FastAPI'],
  status: 'open',
  created_at: '2026-01-02T00:00:00Z',
  updated_at: '2026-01-02T00:00:00Z',
}

const mockJobsPage: PaginatedResponse<JobResponse> = {
  data: [mockJob, mockJob2],
  next_cursor: null,
  has_more: false,
}

export const handlers = [
  http.post('/api/auth/login', () => {
    return HttpResponse.json(mockRecruiter, { status: 200 })
  }),

  http.post('/api/auth/register', () => {
    return HttpResponse.json(mockRecruiter, { status: 201 })
  }),

  http.post('/api/auth/refresh', () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.post('/api/auth/logout', () => {
    return new HttpResponse(null, { status: 204 })
  }),

  http.get('/api/jobs', () => {
    return HttpResponse.json(mockJobsPage, { status: 200 })
  }),

  http.post('/api/jobs', () => {
    return HttpResponse.json(mockJob, { status: 201 })
  }),

  http.get('/api/jobs/:id', ({ params }) => {
    const job = params.id === 'job-1' ? mockJob : { ...mockJob, id: params.id as string }
    return HttpResponse.json(job, { status: 200 })
  }),

  http.put('/api/jobs/:id', ({ params }) => {
    const job = { ...mockJob, id: params.id as string }
    return HttpResponse.json(job, { status: 200 })
  }),

  http.patch('/api/jobs/:id/close', ({ params }) => {
    const job = { ...mockJob, id: params.id as string, status: 'closed' as const }
    return HttpResponse.json(job, { status: 200 })
  }),
]
