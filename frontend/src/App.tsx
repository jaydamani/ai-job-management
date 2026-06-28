import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import ProtectedLayout from './components/ProtectedLayout'

const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const JobsPage = lazy(() => import('./pages/JobsPage'))
const JobFormPage = lazy(() => import('./pages/JobFormPage'))
const CandidatesPage = lazy(() => import('./pages/CandidatesPage'))
const AddCandidatePage = lazy(() => import('./pages/AddCandidatePage'))
const CandidateDetailPage = lazy(() => import('./pages/CandidateDetailPage'))

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
    </div>
  )
}

export default function App() {
  const { isLoading } = useAuth()

  if (isLoading) return <Spinner />

  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/" element={<Navigate to="/jobs" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route element={<ProtectedLayout />}>
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/jobs/new" element={<JobFormPage />} />
          <Route path="/jobs/:jobId" element={<JobFormPage />} />
          <Route path="/jobs/:jobId/candidates" element={<CandidatesPage />} />
          <Route path="/jobs/:jobId/candidates/new" element={<AddCandidatePage />} />
          <Route path="/jobs/:jobId/candidates/:candidateId" element={<CandidateDetailPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
