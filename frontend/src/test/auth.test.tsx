import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { server } from './mocks/server'
import { renderWithProviders } from './utils'
import { AuthProvider } from '../context/AuthContext'
import LoginPage from '../pages/LoginPage'
import App from '../App'

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

// Render LoginPage with a /jobs stub so we can assert navigation happened
function renderLoginWithJobsStub() {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/jobs" element={<div>Jobs Page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// Render the full App starting from a given route
function renderAppAt(initialEntries: string[]) {
  return render(
    <QueryClientProvider client={makeQc()}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Login page', () => {
  it('submits credentials and redirects to /jobs on success', async () => {
    const user = userEvent.setup()
    renderLoginWithJobsStub()

    // Wait for the login form heading to confirm AuthProvider has loaded
    await screen.findByText('Sign in to your account')

    // The label/input are not associated via htmlFor, so use name attribute
    const emailInput = document.querySelector('input[name="email"]') as HTMLInputElement
    const passwordInput = document.querySelector('input[name="password"]') as HTMLInputElement

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')

    await user.click(screen.getByRole('button', { name: /sign in/i }))

    // After a successful POST /auth/login the page navigates to /jobs
    await screen.findByText('Jobs Page')
  })

  it('shows an error message when login returns 401', async () => {
    const user = userEvent.setup()

    server.use(
      http.post('/api/auth/login', () =>
        HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
      )
    )

    renderWithProviders(<LoginPage />, { initialEntries: ['/login'] })

    // Wait for the form to render
    await screen.findByText('Sign in to your account')

    const emailInput = document.querySelector('input[name="email"]') as HTMLInputElement
    const passwordInput = document.querySelector('input[name="password"]') as HTMLInputElement

    await user.type(emailInput, 'bad@example.com')
    await user.type(passwordInput, 'badpassword')

    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await screen.findByText('Invalid credentials')
  })
})

describe('Route protection', () => {
  it('redirects an unauthenticated user visiting /jobs to /login', async () => {
    // refresh returns 204 with no body → recruiter stays null → ProtectedLayout redirects
    renderAppAt(['/jobs'])

    await screen.findByText(/sign in to your account/i)
  })
})
