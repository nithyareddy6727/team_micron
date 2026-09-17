export function formatPercent(value, digits = 1) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '--'
  return `${(numeric * 100).toFixed(digits)}%`
}

export function formatNumber(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return '--'
  return new Intl.NumberFormat('en-US').format(numeric)
}

export function formatDateTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--'
  return date.toLocaleString()
}

export function toRiskTone(value) {
  const normalized = String(value || '').toLowerCase()
  if (normalized.includes('high')) return 'high'
  if (normalized.includes('medium')) return 'medium'
  return 'low'
}

export function normalizePredictionPayload(raw = {}) {
  const probability = Number(raw?.probability ?? raw?.score ?? 0)
  const risk = String(raw?.risk_level ?? raw?.risk ?? (probability >= 0.5 ? 'Churn' : 'Not Churn'))
  const predictionLabel = String(raw?.prediction_label ?? (Number(raw?.prediction ?? 0) === 1 ? 'Churn' : 'Not Churn'))
  return {
    prediction: raw?.prediction ?? (probability >= 0.5 ? 1 : 0),
    predictionLabel,
    probability,
    risk,
    confidence: Number(raw?.confidence_score ?? raw?.confidence ?? probability),
    confidenceLabel: String(raw?.confidence_label ?? 'Medium'),
    latencyMs: Number(raw?.latency_ms ?? raw?.latency ?? 0),
    modelVersion: String(raw?.model_version ?? 'unknown'),
    explanationText: raw?.explanation_text ?? '',
    topFeatures: Array.isArray(raw?.top_features) ? raw.top_features : [],
    recommendations: Array.isArray(raw?.recommendations) ? raw.recommendations : [],
    primaryDriver: raw?.primary_driver || '',
    sector: raw?.sector || 'telecom',
  }
}
