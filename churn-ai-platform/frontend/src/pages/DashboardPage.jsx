import { createElement } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Activity, AlertTriangle, ArrowRight, ArrowUpRight, Clock3, ShieldAlert, ShieldCheck, Sparkles, TrendingDown, TrendingUp, Users, Zap } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { ErrorState } from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'
import { RiskDistributionChart } from '@/components/charts/RiskDistributionChart'
import { TrendChart } from '@/components/charts/TrendChart'
import { getDashboard, getHistory } from '@/services/dashboardService'
import { useApiHealth } from '@/hooks/useApiHealth'
import { useAppStore } from '@/hooks/useAppStore'
import { formatDateTime, formatNumber, formatPercent } from '@/utils/formatters'

function MetricCard({ title, value, hint, icon: Icon, tone = 'blue', trend = 'Updated', delay = 0 }) {
  const tones = {
    blue: 'bg-blue-50 text-[#0A84FF] dark:bg-blue-950/40',
    green: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40',
    amber: 'bg-amber-50 text-amber-600 dark:bg-amber-950/40',
    rose: 'bg-rose-50 text-rose-600 dark:bg-rose-950/40',
    violet: 'bg-violet-50 text-violet-600 dark:bg-violet-950/40',
  }
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay, ease: 'easeOut' }}
    >
      <Card className="relative overflow-hidden transition duration-200 hover:-translate-y-1 hover:shadow-[0_22px_48px_rgba(34,59,112,0.15)]">
        <div className="absolute -right-9 -top-9 h-24 w-24 rounded-full bg-gradient-to-br from-[#0A84FF]/20 to-[#5E5CE6]/20 blur-xl" />
        <div className="relative flex items-start justify-between gap-3">
          <div className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${tones[tone]}`}>
            {createElement(Icon, { size: 19 })}
          </div>
          <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
            <TrendingUp size={13} />{trend}
          </span>
        </div>
        <p className="relative mt-4 text-xs uppercase tracking-[0.14em] text-[#68708a] dark:text-slate-400">{title}</p>
        <p className="relative mt-2 text-3xl font-bold text-[#1D1D1F] dark:text-white">{value}</p>
        <p className="relative mt-2 text-xs text-[#68708a] dark:text-slate-400">{hint}</p>
      </Card>
    </motion.div>
  )
}

export default function DashboardPage() {
  const healthQuery = useApiHealth()
  const sector = useAppStore((state) => state.sector) || 'telecom'

  const dashboardQuery = useQuery({
    queryKey: ['dashboard', 24],
    queryFn: () => getDashboard(24),
  })

  const historyQuery = useQuery({
    queryKey: ['recent-history'],
    queryFn: () => getHistory(8, 0),
  })

  if (dashboardQuery.isLoading) {
    return (
      <div className="grid gap-4">
        <Skeleton className="h-32" />
        <Skeleton className="h-80" />
      </div>
    )
  }

  if (dashboardQuery.isError) {
    return <ErrorState description={dashboardQuery.error.message} onRetry={dashboardQuery.refetch} />
  }

  const dashboard = dashboardQuery.data
  const historyRows = historyQuery.data?.history || []
  const risks = dashboard.risk_distribution || {}
  const highRiskCustomers = dashboard.high_risk_customers || []

  const sectorName = sector === 'saas' ? 'SaaS & Cloud' : sector === 'consumer' ? 'Consumer & Digital' : 'Telecom & Broadband'

  const metrics = [
    { title: 'Total Customers', value: formatNumber(dashboard.total_customers), hint: 'Accounts tracked in current workspace', icon: Users, tone: 'blue', trend: 'Live' },
    { title: 'High-Risk Segment', value: formatNumber(dashboard.high_risk_count), hint: 'Immediate retention intervention required', icon: ShieldAlert, tone: 'rose', trend: `${formatPercent(dashboard.high_risk_percentage / 100)}` },
    { title: 'Medium-Risk Segment', value: formatNumber(risks.medium || 0), hint: 'Nurture & engagement check-in required', icon: AlertTriangle, tone: 'amber', trend: 'Watchlist' },
    { title: 'Low-Risk Segment', value: formatNumber(risks.low || 0), hint: 'Stable and healthy accounts', icon: ShieldCheck, tone: 'green', trend: 'Healthy' },
    { title: 'Avg Churn Probability', value: formatPercent(dashboard.churn_rate), hint: 'Portfolio aggregate predicted churn rate', icon: Sparkles, tone: 'violet', trend: 'AI Metric' },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-bold uppercase tracking-wider text-[#0A84FF] dark:bg-blue-950/60">
              {sectorName}
            </span>
            <span className="text-xs text-[#68708a] dark:text-slate-400">
              Customer Churn Prediction Agent
            </span>
          </div>
          <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-[#1D1D1F] dark:text-white">
            Retention Command Center
          </h1>
          <p className="mt-1 text-sm text-[#68708a] dark:text-slate-400">
            <strong>PREDICT &rarr; EXPLAIN &rarr; PRIORITIZE &rarr; ACT</strong>: Identify churn risk and dispatch targeted retention plays.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/customers?risk=high"
            className="inline-flex items-center gap-1.5 rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2 text-xs font-bold text-rose-700 transition hover:bg-rose-100 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300"
          >
            <ShieldAlert size={15} /> View High-Risk Queue ({dashboard.high_risk_count})
          </a>
          <a
            href="/prediction"
            className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-[#0A84FF] to-[#5E5CE6] px-4 py-2 text-xs font-bold text-white shadow-[0_8px_18px_rgba(10,132,255,0.25)] transition hover:opacity-95"
          >
            New Prediction <ArrowUpRight size={15} />
          </a>
        </div>
      </div>

      {/* Overview Cards: Total, High, Medium, Low, Avg Probability */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {metrics.map((metric, index) => (
          <MetricCard key={metric.title} {...metric} delay={index * 0.04} />
        ))}
      </div>

      {/* Visual Analytics Row */}
      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <Card title="Risk Distribution" subtitle="Portfolio segmentation across Low, Medium, and High risk tiers">
          <RiskDistributionChart data={dashboard.risk_distribution || {}} />
        </Card>
        <Card title="Prediction Throughput" subtitle="Hourly inference distribution">
          <TrendChart data={dashboard.prediction_trend || dashboard.trend || []} />
        </Card>
      </div>

      {/* REQUIREMENT 6: HIGH-RISK CUSTOMER IDENTIFICATION TABLE (WHO TO CONTACT FIRST) */}
      <Card
        title="High-Risk Prioritization Queue"
        subtitle="Ranked list of accounts requiring immediate retention intervention (Who to contact first)"
        className="border-rose-100 dark:border-rose-950/40"
      >
        <div className="overflow-x-auto">
          {highRiskCustomers.length > 0 ? (
            <table className="w-full min-w-[840px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-bold uppercase tracking-wider text-[#69708b] dark:border-slate-700 dark:text-slate-400">
                  <th className="py-3 pr-3">Priority</th>
                  <th className="py-3 pr-3">Customer ID</th>
                  <th className="py-3 pr-3">Churn Probability</th>
                  <th className="py-3 pr-3">Risk Tier</th>
                  <th className="py-3 pr-3">Primary Churn Driver</th>
                  <th className="py-3 pr-3">Recommended Retention Action</th>
                  <th className="py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {highRiskCustomers.map((cust, index) => (
                  <tr key={cust.customer_id} className="transition hover:bg-rose-50/40 dark:hover:bg-rose-950/20">
                    <td className="py-3.5 pr-3 font-mono text-xs font-bold text-rose-600">
                      #{index + 1}
                    </td>
                    <td className="py-3.5 pr-3 font-semibold text-[#1D1D1F] dark:text-white">
                      {cust.customer_id}
                    </td>
                    <td className="py-3.5 pr-3 font-extrabold text-rose-600">
                      {formatPercent(cust.probability)}
                    </td>
                    <td className="py-3.5 pr-3">
                      <span className="rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-700 dark:bg-rose-950/70 dark:text-rose-300">
                        HIGH RISK
                      </span>
                    </td>
                    <td className="py-3.5 pr-3 text-xs font-medium text-slate-700 dark:text-slate-300">
                      <span className="inline-flex items-center gap-1">
                        <Zap size={13} className="text-amber-500" />
                        {cust.primary_driver || 'Tenure & Cost Sensitivity'}
                      </span>
                    </td>
                    <td className="py-3.5 pr-3 text-xs text-slate-600 dark:text-slate-300">
                      {cust.recommended_action || 'Offer retention discount and schedule follow-up.'}
                    </td>
                    <td className="py-3.5 text-right">
                      <a
                        href={`/prediction`}
                        className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:bg-[#0A84FF] hover:text-white dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-[#0A84FF]"
                      >
                        Review <ArrowRight size={12} />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-6 text-center text-sm text-[#69708b] dark:text-slate-400">
              No critical high-risk accounts identified in the current snapshot.
            </div>
          )}
        </div>
      </Card>

      {/* Recent Predictions History */}
      <Card title="Recent Prediction Events" subtitle="Audit trail of recent inference requests">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs font-bold uppercase tracking-wider text-[#69708b] dark:border-slate-700 dark:text-slate-400">
                <th className="py-3 pr-3">Customer ID</th>
                <th className="py-3 pr-3">Risk Level</th>
                <th className="py-3 pr-3">Probability</th>
                <th className="py-3 pr-3">Inference Latency</th>
                <th className="py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {historyRows.map((row) => (
                <tr key={`${row.customer_id}-${row.timestamp}`} className="text-[#22252f] dark:text-slate-200">
                  <td className="py-3 pr-3 font-mono font-medium">{row.customer_id}</td>
                  <td className="py-3 pr-3 font-semibold">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${
                      String(row.risk_level || row.risk).toLowerCase() === 'high'
                        ? 'bg-rose-100 text-rose-700 dark:bg-rose-950 dark:text-rose-300'
                        : String(row.risk_level || row.risk).toLowerCase() === 'medium'
                        ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                        : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                    }`}>
                      {row.risk_level || row.risk || '--'}
                    </span>
                  </td>
                  <td className="py-3 pr-3 font-semibold">{formatPercent(row.probability)}</td>
                  <td className="py-3 pr-3 text-xs text-slate-500">{Number(row.latency_ms || 0).toFixed(1)} ms</td>
                  <td className="py-3 text-xs text-slate-500">{formatDateTime(row.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
