import apiClient, { unwrapApiEnvelope } from '@/services/apiClient'

export async function getAnalytics(hours = 24) {
  const { data } = await apiClient.get('/analytics', { params: { hours } })
  return unwrapApiEnvelope(data)
}

export async function getCustomers(search = '') {
  const { data } = await apiClient.get('/customers', {
    params: {
      limit: 250,
      offset: 0,
      search: search || undefined,
    },
  })
  return unwrapApiEnvelope(data)
}
