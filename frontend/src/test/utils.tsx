import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../context/AuthContext'

export function renderWithProviders(
  ui: React.ReactElement,
  { initialEntries = ['/'] }: { initialEntries?: string[] } = {}
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })

  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={initialEntries}>
        <AuthProvider>{ui}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
}
