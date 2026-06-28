import axios from 'axios'
import type { AxiosRequestConfig } from 'axios'

interface RetryableRequestConfig extends AxiosRequestConfig {
  _retry?: boolean
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true,
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as RetryableRequestConfig

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        await axios.post(
          `${import.meta.env.VITE_API_URL || '/api'}/auth/refresh`,
          undefined,
          { withCredentials: true }
        )
        return api(originalRequest)
      } catch {
        window.dispatchEvent(new CustomEvent('auth:logout'))
        return Promise.reject(error)
      }
    }

    if (error.response?.status === 401 && originalRequest._retry) {
      window.dispatchEvent(new CustomEvent('auth:logout'))
    }

    return Promise.reject(error)
  }
)

export default api
