export const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
export const REQUEST_TIMEOUT_MS = 10000
export const POWERBI_CONFIG = {
  reportId: import.meta.env.VITE_POWERBI_REPORT_ID || '',
  embedUrl: import.meta.env.VITE_POWERBI_EMBED_URL || '',
  accessToken: import.meta.env.VITE_POWERBI_ACCESS_TOKEN || '',
  tokenType: (import.meta.env.VITE_POWERBI_TOKEN_TYPE || 'Embed').toLowerCase(),
  tableName: import.meta.env.VITE_POWERBI_TABLE_NAME || 'customers',
  riskColumn: import.meta.env.VITE_POWERBI_RISK_COLUMN || 'risk_level',
  contractColumn: import.meta.env.VITE_POWERBI_CONTRACT_COLUMN || 'contract_type',
  customerColumn: import.meta.env.VITE_POWERBI_CUSTOMER_COLUMN || 'customer_id',
  drillthroughPage: import.meta.env.VITE_POWERBI_DRILLTHROUGH_PAGE || '',
  slicerEnabled: (import.meta.env.VITE_POWERBI_SLICER_ENABLED || 'true').toLowerCase() === 'true',
}

export const QUERY_DEFAULTS = {
  staleTime: 60000,
  gcTime: 300000,
  retry: 1,
  retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
  refetchOnWindowFocus: false,
  refetchOnReconnect: true,
}
