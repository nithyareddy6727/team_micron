export function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--'
  return `${(Number(value) * 100).toFixed(1)}%`
}

export function formatDate(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return date.toLocaleString()
}

export function toRiskBand(probability) {
  const p = Number(probability) || 0
  if (p >= 0.7) return 'high'
  if (p >= 0.3) return 'medium'
  return 'low'
}

export function toCsv(rows) {
  const header = ['customer_id', 'prediction', 'probability', 'confidence_score', 'risk_level', 'timestamp']
  const lines = rows.map((row) => header.map((key) => JSON.stringify(row[key] ?? '')).join(','))
  return [header.join(','), ...lines].join('\n')
}
