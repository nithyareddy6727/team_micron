import axios from 'axios'
import { useAppStore } from '@/hooks/useAppStore'

const DEFAULT_TIMEOUT = 15000

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: DEFAULT_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const apiBaseUrl = useAppStore.getState().apiBaseUrl
  config.baseURL = apiBaseUrl || config.baseURL

  const apiKey = import.meta.env.VITE_API_KEY
  if (apiKey) {
    config.headers['x-api-key'] = apiKey
  }

  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const fallbackMessage = error?.message || 'Network request failed'
    const message =
      error?.response?.data?.error ||
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      fallbackMessage

    return Promise.reject(new Error(message))
  },
)

export function unwrapApiEnvelope(payload) {
  if (!payload || payload.success !== true) {
    throw new Error(payload?.error || 'Backend returned invalid API envelope')
  }
  return payload.data
}

export default apiClient
