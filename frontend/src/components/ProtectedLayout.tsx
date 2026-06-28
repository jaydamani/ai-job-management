import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Navbar from './Navbar'

export default function ProtectedLayout() {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main>
        <Outlet />
      </main>
    </div>
  )
}
