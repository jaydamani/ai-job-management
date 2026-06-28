import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authApi } from '../api/auth'
import type { AxiosError } from 'axios'

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  name: z.string().optional(),
})

type FormData = z.infer<typeof schema>

export default function RegisterPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [apiError, setApiError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    setApiError(null)
    try {
      const recruiter = await authApi.register(data)
      login(recruiter)
      navigate('/jobs', { replace: true })
    } catch (err) {
      const axiosErr = err as AxiosError<{ detail?: string }>
      setApiError(axiosErr.response?.data?.detail ?? 'Registration failed. Email may already be in use.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <h1 className="text-3xl font-bold text-center text-gray-900 mb-2">Gappeo</h1>
        <p className="text-center text-gray-500 mb-8">Create your recruiter account</p>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="bg-white shadow rounded-lg p-8 space-y-5"
        >
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
              Name <span className="text-gray-400">(optional)</span>
            </label>
            <input
              {...register('name')}
              id="name"
              type="text"
              autoComplete="name"
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              {...register('email')}
              id="email"
              type="email"
              autoComplete="email"
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              {...register('password')}
              id="password"
              type="password"
              autoComplete="new-password"
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {errors.password && (
              <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>

          {apiError && (
            <p className="text-sm text-red-600 text-center">{apiError}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-blue-600 text-white py-2 rounded-md font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
