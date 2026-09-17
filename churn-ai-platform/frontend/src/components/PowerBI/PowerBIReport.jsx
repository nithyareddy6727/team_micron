import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { models } from 'powerbi-client'
import { PowerBIEmbed } from 'powerbi-client-react'
import { getPowerBIEmbedConfig } from '@/services/powerBIService'
import { ErrorState } from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'

export function PowerBIReport() {
  const embedQuery = useQuery({
    queryKey: ['powerbi-embed-config'],
    queryFn: () => getPowerBIEmbedConfig(false),
    staleTime: 300000,
  })

  const config = useMemo(() => {
    if (!embedQuery.data) return null

    return {
      type: 'report',
      id: embedQuery.data.reportId,
      embedUrl: embedQuery.data.embedUrl,
      accessToken: embedQuery.data.accessToken,
      tokenType: models.TokenType.Embed,
      settings: {
        panes: {
          filters: { visible: false },
          pageNavigation: { visible: true },
        },
        background: models.BackgroundType.Transparent,
      },
    }
  }, [embedQuery.data])

  if (embedQuery.isLoading) {
    return <Skeleton className="h-[420px] w-full" />
  }

  if (embedQuery.isError) {
    return <ErrorState title="Power BI unavailable" description={embedQuery.error.message} onRetry={embedQuery.refetch} actionLabel="Retry embed" />
  }

  if (!config?.id || !config.embedUrl || !config.accessToken) {
    return (
      <ErrorState
        title="Power BI not configured"
        description="Configure backend POWERBI_TENANT_ID, POWERBI_CLIENT_ID, POWERBI_CLIENT_SECRET, POWERBI_WORKSPACE_ID, POWERBI_REPORT_ID, and POWERBI_EMBED_URL so /powerbi/embed-config can return a valid embed token."
      />
    )
  }

  return (
    <div className="overflow-hidden rounded-3xl border border-white/60 bg-white/70 p-2 shadow-[0_15px_40px_rgba(15,44,97,0.12)] backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/70">
      <PowerBIEmbed embedConfig={config} cssClassName="h-[420px] w-full rounded-2xl" />
    </div>
  )
}
