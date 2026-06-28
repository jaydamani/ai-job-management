import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { recruiter, logout } = useAuth()

  const displayName = recruiter?.name || recruiter?.email || 'Account'

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link
          to="/jobs"
          className="text-xl font-bold text-blue-600 hover:text-blue-700 transition-colors"
        >
          Gappeo
        </Link>

        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600 hidden sm:block">{displayName}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-600 hover:text-gray-900 font-medium transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  )
}
