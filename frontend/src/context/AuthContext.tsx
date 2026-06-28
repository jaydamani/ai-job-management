import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useRef,
} from 'react'
import { useNavigate } from 'react-router-dom'
import type { RecruiterResponse } from '../types'
import { authApi } from '../api/auth'

interface AuthContextValue {
  recruiter: RecruiterResponse | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (recruiter: RecruiterResponse) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [recruiter, setRecruiter] = useState<RecruiterResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  const logoutCalledRef = useRef(false)

  const logout = useCallback(async () => {
    if (logoutCalledRef.current) return
    logoutCalledRef.current = true
    try {
      await authApi.logout()
    } catch {
      // ignore errors on logout
    } finally {
      setRecruiter(null)
      logoutCalledRef.current = false
      navigate('/login')
    }
  }, [navigate])

  // On mount: attempt a refresh to see if there is a valid session
  useEffect(() => {
    authApi
      .refresh()
      .catch(() => {
        // No valid session — isAuthenticated stays false
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [])

  // Listen for the interceptor's forced-logout event
  useEffect(() => {
    const handler = () => {
      setRecruiter(null)
      navigate('/login')
    }
    window.addEventListener('auth:logout', handler)
    return () => window.removeEventListener('auth:logout', handler)
  }, [navigate])

  const login = useCallback((r: RecruiterResponse) => {
    setRecruiter(r)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        recruiter,
        isLoading,
        isAuthenticated: recruiter !== null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
