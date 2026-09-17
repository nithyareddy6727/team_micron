import apiClient, { unwrapApiEnvelope } from '@/services/apiClient'

const PAGE_SIZE = 500

export async function getAllHistory() {
  let offset = 0
  let total = 1
  const rows = []

  while (offset < total) {
    const { data } = await apiClient.get('/history', {
      params: {
        limit: PAGE_SIZE,
        offset,
      },
    })

    const payload = unwrapApiEnvelope(data)
    total = Number(payload?.total || 0)
    const historyRows = Array.isArray(payload?.history) ? payload.history : []
    rows.push(...historyRows)

    offset += PAGE_SIZE
    if (historyRows.length === 0) break
  }

  return rows
}
