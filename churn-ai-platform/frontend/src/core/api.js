import axios from 'axios'
import { DEFAULT_API_BASE_URL, REQUEST_TIMEOUT_MS } from '@/core/config'

export const API = axios.create({
  baseURL: DEFAULT_API_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
})

const isDev = import.meta.env.DEV

const log = (...args) => {
  if (isDev) {
    console.info(...args)
  }
}

const logError = (...args) => {
  if (isDev) {
    console.error(...args)
  }
}

API.interceptors.response.use(
  (response) => {
    log('[api] Response', {
      status: response.status,
      url: response.config?.url,
      data: response.data,
    })
    return response
  },
  (error) => {
    logError('[api] Error', {
      message: error?.message,
      code: error?.code,
      status: error?.response?.status,
      url: error?.config?.url,
      data: error?.response?.data,
    })
    const message =
      error?.response?.data?.error ||
      error?.response?.data?.detail ||
      error?.response?.data?.message ||
      error?.message ||
      'Request failed'
    return Promise.reject(new Error(message))
  },
)

export const setApiBaseUrl = (url) => {
  if (url?.trim()) API.defaults.baseURL = url.trim()
}

const unwrapEnvelope = (payload) => {
  if (!payload || payload.success !== true || payload.error !== null) {
    throw new Error(payload?.error || 'API contract violation')
  }
  return payload.data
}

export const fetchCustomers = async (params = {}) => {
  log('[api] GET /customers request', params)
  const { data } = await API.get('/customers', { params })
  log('[api] GET /customers response', data)
  return unwrapEnvelope(data)
}

export const predictCustomer = async (idOrPayload) => {
  const payload =
    typeof idOrPayload === 'string'
      ? { customer_id: idOrPayload, features: { customer_id: idOrPayload }, return_proba: true }
      : idOrPayload

  const normalizedPayload = payload.features
    ? payload
    : {
        customer_id: payload.customer_id || 'manual-input',
        features: payload,
        return_proba: true,
        explain: true,
      }

  log('[api] POST /predict request', normalizedPayload)
  try {
    const { data } = await API.post('/predict', normalizedPayload)
    log('[api] POST /predict response', data)
    return unwrapEnvelope(data)
  } catch (error) {
    logError('[api] POST /predict failed', error)
    throw error
  }
}

export const batchPredict = async (data) => {
  log('[api] POST /predict/batch request', data)
  const response = await API.post('/predict/batch', data)
  log('[api] POST /predict/batch response', response.data)
  return unwrapEnvelope(response.data)
}

export const fetchHistory = async (params = {}) => {
  log('[api] GET /history request', params)
  const { data } = await API.get('/history', { params })
  log('[api] GET /history response', data)
  return unwrapEnvelope(data)
}

export const fetchMetrics = async () => {
  const { data } = await API.get('/metrics/app')
  return unwrapEnvelope(data)
}

export const fetchHealth = async () => {
  const { data } = await API.get('/health')
  return unwrapEnvelope(data)
}

export const fetchDashboardMetrics = async (params = { hours: 24 }) => {
  const { data } = await API.get('/dashboard', { params })
  return unwrapEnvelope(data)
}

export const fetchAnalytics = async (params = { hours: 24 }) => {
  const { data } = await API.get('/analytics', { params })
  return unwrapEnvelope(data)
}

export const fetchModelHealth = async () => {
  const { data } = await API.get('/model-health')
  return unwrapEnvelope(data)
}

export const fetchSystemHealth = async () => {
  const { data } = await API.get('/system-health')
  return data
}

export const retrainModel = async (params = {}) => {
  const { data } = await API.post('/retrain', null, { params })
  return unwrapEnvelope(data)
}

export const fetchPowerBIEmbedConfig = async (params = {}) => {
  const { data } = await API.get('/powerbi/embed-config', { params })
  return unwrapEnvelope(data)
}

export default API
