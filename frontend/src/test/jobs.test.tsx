import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { server } from './mocks/server'
import { AuthProvider } from '../context/AuthContext'
import { mockJob, mockJob2, mockRecruiter } from './mocks/handlers'
import JobsPage from '../pages/JobsPage'
import JobFormPage from '../pages/JobFormPage'
import type { PaginatedResponse, JobResponse } from '../types'

// IntersectionObserver is not available in jsdom — provide a no-op stub
beforeAll(() => {
  global.IntersectionObserver = class IntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
    readonly root = null
    readonly rootMargin = ''
    readonly thresholds = []
    takeRecords() { return [] }
  }
})

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

// Render a page with all providers.
// Optionally override the mock recruiter so the AuthProvider knows the user is logged in.
function renderPage(ui: React.ReactElement, initialEntries = ['/']) {
  // We manually pre-seed the recruiter by overriding the refresh handler
  // to act as if there is an active session. AuthProvider only calls refresh
  // on mount; it does NOT set the recruiter from the refresh response —
  // recruiter state is set by calling login(). So to get isAuthenticated=true,
  // we need to wrap in a context where recruiter is already set.
  // The simplest approach: render the page directly (not through ProtectedLayout)
  // so auth gating is bypassed. Pages themselves don't check auth.
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('JobsPage', () => {
  it('renders a list of jobs from the API', async () => {
    renderPage(<JobsPage />)

    // Wait for jobs to appear
    await screen.findByText('Senior Frontend Engineer')
    expect(screen.getByText('Backend Engineer')).toBeInTheDocument()
  })

  it('shows empty state when no jobs are returned', async () => {
    const emptyPage: PaginatedResponse<JobResponse> = {
      data: [],
      next_cursor: null,
      has_more: false,
    }

    server.use(
      http.get('/api/jobs', () => HttpResponse.json(emptyPage, { status: 200 }))
    )

    renderPage(<JobsPage />)

    await screen.findByText(/no jobs yet/i)
  })

  it('shows job status badge', async () => {
    renderPage(<JobsPage />)

    const badges = await screen.findAllByText('open')
    expect(badges.length).toBeGreaterThan(0)
  })
})

describe('JobFormPage — create mode', () => {
  it('submits the form and navigates to the new job', async () => {
    const user = userEvent.setup()
    let capturedBody: unknown = null

    // Intercept the POST and capture the request body
    server.use(
      http.post('/api/jobs', async ({ request }) => {
        capturedBody = await request.json()
        return HttpResponse.json(mockJob, { status: 201 })
      })
    )

    render(
      <QueryClientProvider client={makeQc()}>
        <MemoryRouter initialEntries={['/jobs/new']}>
          <AuthProvider>
            <Routes>
              <Route path="/jobs/new" element={<JobFormPage />} />
              <Route path="/jobs/:jobId" element={<div data-testid="job-detail">Job Detail</div>} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )

    // Fill in required fields
    const titleInput = await screen.findByPlaceholderText(/senior frontend engineer/i)
    await user.type(titleInput, 'Test Engineer')

    const descInput = screen.getByPlaceholderText(/describe responsibilities/i)
    await user.type(descInput, 'A great role for testing')

    await user.click(screen.getByRole('button', { name: /create job/i }))

    // Should navigate to the new job detail page
    await screen.findByTestId('job-detail')

    // The body sent to the API should include title and description
    expect(capturedBody).toMatchObject({
      title: 'Test Engineer',
      description: 'A great role for testing',
    })
  })

  it('shows validation errors when required fields are empty', async () => {
    const user = userEvent.setup()

    renderPage(<JobFormPage />, ['/jobs/new'])

    await user.click(await screen.findByRole('button', { name: /create job/i }))

    await screen.findByText('Title is required')
    expect(screen.getByText('Description is required')).toBeInTheDocument()
  })
})
