import api from './client'
import type { RecruiterResponse } from '../types'

export interface LoginBody {
  email: string
  password: string
}

export interface RegisterBody {
  email: string
  password: string
  name?: string
}

export const authApi = {
  login: (body: LoginBody) =>
    api.post<RecruiterResponse>('/auth/login', body).then((r) => r.data),

  register: (body: RegisterBody) =>
    api.post<RecruiterResponse>('/auth/register', body).then((r) => r.data),

  refresh: () => api.post<RecruiterResponse>('/auth/refresh').then((r) => r.data),

  logout: () => api.post('/auth/logout'),
}

// Standalone named exports matching the WI-007 API contract
export const loginApi = (email: string, password: string): Promise<RecruiterResponse> =>
  authApi.login({ email, password })

export const registerApi = (email: string, password: string, name?: string): Promise<RecruiterResponse> =>
  authApi.register({ email, password, name })

export const logoutApi = (): Promise<void> =>
  authApi.logout().then(() => undefined)
