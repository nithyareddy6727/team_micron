import apiClient, { unwrapApiEnvelope } from '@/services/apiClient'

const PAGE_SIZE = 500

export async function getAllCustomers({ search = '', risk_level, sector } = {}) {
  let offset = 0
  let total = 1
  const rows = []

  while (offset < total) {
    const { data } = await apiClient.get('/customers', {
      params: {
        limit: PAGE_SIZE,
        offset,
        search: search || undefined,
        risk_level: risk_level || undefined,
        sector: sector || undefined,
      },
    })

    const payload = unwrapApiEnvelope(data)
    total = Number(payload?.total || 0)
    const customers = Array.isArray(payload?.customers) ? payload.customers : []
    rows.push(...customers)

    offset += PAGE_SIZE
    if (customers.length === 0) break
  }

  return {
    total: rows.length,
    customers: rows,
  }
}
