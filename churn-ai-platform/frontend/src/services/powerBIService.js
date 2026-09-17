import apiClient, { unwrapApiEnvelope } from '@/services/apiClient'

export async function getPowerBIEmbedConfig(refresh = false) {
  const { data } = await apiClient.get('/powerbi/embed-config', {
    params: { refresh },
  })

  const backendConfig = unwrapApiEnvelope(data)
  const envConfig = {
    reportId: import.meta.env.VITE_POWERBI_REPORT_ID || import.meta.env.REACT_APP_POWERBI_REPORT_ID || '',
    clientId: import.meta.env.VITE_POWERBI_CLIENT_ID || import.meta.env.REACT_APP_POWERBI_CLIENT_ID || '',
    tenantId: import.meta.env.VITE_POWERBI_TENANT_ID || import.meta.env.REACT_APP_POWERBI_TENANT_ID || '',
  }

  const normalizedBackend = {
    reportId: backendConfig.reportId || backendConfig.report_id || '',
    embedUrl: backendConfig.embedUrl || backendConfig.embed_url || '',
    accessToken: backendConfig.accessToken || backendConfig.access_token || '',
    tokenType: backendConfig.tokenType || backendConfig.token_type || 'Embed',
    expiresAt: backendConfig.expiresAt || backendConfig.expires_at || null,
  }

  return {
    ...normalizedBackend,
    clientId: envConfig.clientId,
    tenantId: envConfig.tenantId,
    reportId: normalizedBackend.reportId || envConfig.reportId || '',
  }
}
