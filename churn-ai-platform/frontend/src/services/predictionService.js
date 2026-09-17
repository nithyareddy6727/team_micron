import apiClient, { unwrapApiEnvelope } from '@/services/apiClient'

function coerceNumber(value) {
  if (value === null || value === undefined || value === '') return value
  if (typeof value === 'number') return value
  const parsed = Number(value)
  return Number.isNaN(parsed) ? value : parsed
}

function normalizeFeatures(features = {}) {
  const input = { ...features }

  const monthly =
    input.monthly_charges ??
    input.monthly_charge ??
    input.MonthlyCharges ??
    input.MonthlyCharge

  const tenure = input.tenure ?? input.tenure_in_months ?? input.Tenure
  const age = input.age ?? input.Age
  const contractType = input.contract_type ?? input.contract ?? input.Contract
  const internetService = input.internet_service ?? input.InternetService
  const paymentMethod = input.payment_method ?? input.PaymentMethod

  const normalized = {
    ...input,
    age: coerceNumber(age),
    tenure: coerceNumber(tenure),
    monthly_charges: coerceNumber(monthly),
  }

  if (contractType !== undefined) normalized.contract_type = contractType
  if (internetService !== undefined) normalized.internet_service = internetService
  if (paymentMethod !== undefined) normalized.payment_method = paymentMethod

  return Object.fromEntries(Object.entries(normalized).filter(([, value]) => value !== undefined))
}

export async function predict(features) {
  const normalizedFeatures = normalizeFeatures(features)
  const sector = features?.sector || 'telecom'
  const payload = {
    customer_id: normalizedFeatures.customer_id || 'manual-input',
    features: normalizedFeatures,
    sector,
    return_proba: true,
    explain: true,
  }

  const { data } = await apiClient.post('/predict', payload)
  return unwrapApiEnvelope(data)
}

export async function submitAsyncBatch(rows, options = {}) {
  const payload = {
    rows: rows.map((row) => {
      const normalized = normalizeFeatures(row.features || row)
      return {
        customer_id: row.customer_id || normalized.customer_id || 'manual-input',
        features: normalized,
      }
    }),
    return_proba: options.returnProba ?? true,
    explain: options.explain ?? false,
    sector: options.sector ?? 'telecom',
  }

  const { data } = await apiClient.post('/predict/batch/async', payload)
  return unwrapApiEnvelope(data)
}

export async function uploadBatchCsv(file, options = {}) {
  const formData = new FormData()
  formData.append('file', file)

  const params = new URLSearchParams({
    return_proba: String(options.returnProba ?? true),
    explain: String(options.explain ?? false),
    sector: String(options.sector ?? 'telecom'),
  })

  const { data } = await apiClient.post(`/predict/batch/upload?${params.toString()}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return unwrapApiEnvelope(data)
}

export async function getBatchJobStatus(jobId) {
  const { data } = await apiClient.get(`/predict/batch/jobs/${jobId}`)
  return unwrapApiEnvelope(data)
}
