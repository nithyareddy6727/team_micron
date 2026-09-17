import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, BrainCircuit, CircleGauge, Clock3, Download, Filter, ShieldAlert, Users } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { ErrorState } from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'
import { RiskDistributionChart } from '@/components/charts/RiskDistributionChart'
import { TrendChart } from '@/components/charts/TrendChart'
import { ExecutiveSummary } from '@/components/model-insights/ExecutiveSummary'
import { FeatureImportancePanel } from '@/components/model-insights/FeatureImportancePanel'
import { KpiCard } from '@/components/model-insights/KpiCard'
import { RecentPredictionsTable } from '@/components/model-insights/RecentPredictionsTable'
import { getAnalytics } from '@/services/analyticsService'
import { getHealth, getHistory } from '@/services/dashboardService'
import { formatNumber, formatPercent } from '@/utils/formatters'

const timeRanges = [{ label: 'Today', hours: 24 }, { label: '7 Days', hours: 168 }, { label: '30 Days', hours: 168 }, { label: '90 Days', hours: 168 }]
const selectOptions = [['Customer segment', 'All customers'], ['City', 'All cities'], ['Contract type', 'All contracts'], ['Internet type', 'All types'], ['Payment method', 'All methods']]

function SelectControl({ label, value }) { return <label className="min-w-36 flex-1 text-xs font-medium text-slate-500">{label}<select defaultValue="" className="mt-1.5 block w-full rounded-xl border border-slate-200 bg-white/80 px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"><option value="">{value}</option></select></label> }

export default function AnalyticsPage() {
  const [hours, setHours] = useState(24)
  const analyticsQuery = useQuery({ queryKey: ['analytics', hours], queryFn: () => getAnalytics(hours) })
  const healthQuery = useQuery({ queryKey: ['insights-health'], queryFn: getHealth, retry: 1 })
  const historyQuery = useQuery({ queryKey: ['insights-history'], queryFn: () => getHistory(6, 0), retry: 1 })
  const analytics = analyticsQuery.data
  const distribution = analytics?.risk_distribution || {}
  const totalRisk = Object.values(distribution).reduce((total, value) => total + Number(value || 0), 0)
  const highRisk = Number(distribution.high || 0)
  const averageRisk = totalRisk ? highRisk / totalRisk : null
  const trendValues = useMemo(() => (analytics?.trend || []).map((item) => Number(item.prediction_count || 0)), [analytics])
  const history = historyQuery.data?.history || []

  if (analyticsQuery.isLoading) return <div className="space-y-5"><Skeleton className="h-72" /><Skeleton className="h-56" /><Skeleton className="h-80" /></div>
  if (analyticsQuery.isError) return <ErrorState description={analyticsQuery.error.message} onRetry={analyticsQuery.refetch} actionLabel="Retry model insights" />

  return <div className="space-y-5 pb-4">
    <section aria-labelledby="insights-title" className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-600 dark:text-blue-300">AI Intelligence Console</p><h1 id="insights-title" className="mt-1 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">AI Intelligence &amp; Model Insights</h1><p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Monitor model health, prediction quality, customer risk trends, and business impact in real time.</p></div><Button variant="ghost" aria-label="Export dashboard"><Download size={17} /> <span className="ml-2">Export dashboard</span></Button></section>

    <ExecutiveSummary analytics={analytics} health={healthQuery.data} />

    <Card title="Analytics filters" subtitle="Time range updates live trend and feature-impact data. Other filter dimensions will activate when supported by the API."><div className="flex flex-wrap items-end gap-3"><div className="flex flex-wrap gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800" role="group" aria-label="Time range">{timeRanges.map((range) => <button key={range.label} onClick={() => setHours(range.hours)} className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${hours === range.hours ? 'bg-white text-blue-700 shadow-sm dark:bg-slate-700 dark:text-blue-200' : 'text-slate-500 hover:text-slate-800 dark:hover:text-white'}`}>{range.label}</button>)}<button className="rounded-lg px-3 py-2 text-xs font-semibold text-slate-400" disabled>Custom</button></div>{selectOptions.map(([label, value]) => <SelectControl key={label} label={label} value={value} />)}<Button variant="subtle" aria-label="Apply filters"><Filter size={16} /><span className="ml-2">Apply</span></Button></div></Card>

    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3"><KpiCard label="Total customers" value={formatNumber(analytics.total_customers)} icon={Users} detail="Current customer population" sparkline={trendValues} /><KpiCard label="Predictions" value={formatNumber(analytics.total_predictions)} icon={Activity} detail={`${hours}-hour observation window`} sparkline={trendValues} /><KpiCard label="High-risk customers" value={formatNumber(highRisk)} icon={ShieldAlert} tone="rose" detail={totalRisk ? `${formatPercent(highRisk / totalRisk)} of scored customers` : 'No scored customers'} sparkline={trendValues} /><KpiCard label="Average churn probability" value={averageRisk == null ? 'Not Available' : formatPercent(averageRisk)} icon={CircleGauge} tone="rose" detail="High-risk share proxy" /><KpiCard label="Model confidence" value="Not Available" icon={BrainCircuit} detail="Not returned by analytics API" /><KpiCard label="Response time" value="Not Available" icon={Clock3} detail="Not returned by analytics API" /></div>

    <div className="grid gap-5 xl:grid-cols-[1.35fr_.85fr]"><Card title="Prediction trend" subtitle={`Prediction activity across the last ${hours} hours`}><TrendChart data={analytics.trend || []} /></Card><Card title="Risk distribution" subtitle="Scored customers by current risk band"><RiskDistributionChart data={distribution} showLegend /></Card></div>

    <div className="grid gap-5 xl:grid-cols-[1.1fr_.9fr]"><FeatureImportancePanel features={analytics.top_features || []} /><div className="space-y-5"><Card title="Why does the AI make these predictions?" subtitle="SHAP explainability, in plain language"><p className="text-sm leading-6 text-slate-600 dark:text-slate-300">The AI compares each customer with historical customer behaviour. It weighs customer satisfaction, monthly bill, contract type, relationship length, and internet usage differently for every prediction.</p><p className="mt-3 text-sm font-medium text-slate-800 dark:text-slate-100">This explanation helps retention teams understand the factors behind risk—without needing to interpret model mathematics.</p></Card><Card title="Business insights" subtitle="Signals from the current observation window"><ul className="space-y-3 text-sm text-slate-600 dark:text-slate-300"><li>• {highRisk ? `${formatNumber(highRisk)} high-risk customers need prioritised retention outreach.` : 'No high-risk predictions recorded in this view.'}</li><li>• {analytics.top_features?.[0] ? `${String(analytics.top_features[0].feature).replaceAll('_', ' ')} is the strongest recorded risk signal.` : 'Feature signals will appear as prediction explanations are recorded.'}</li><li>• Model drift is {healthQuery.data?.model?.drift_detected ? 'flagged for review.' : 'within the expected production range.'}</li></ul></Card></div></div>

    <div className="grid gap-5 xl:grid-cols-[.8fr_1.2fr]"><Card title="Recommended actions" subtitle="Retention priorities informed by current risk"><ol className="space-y-3 text-sm text-slate-600 dark:text-slate-300"><li><strong className="text-slate-900 dark:text-white">01.</strong> Focus campaigns on high-risk customers first.</li><li><strong className="text-slate-900 dark:text-white">02.</strong> Encourage longer-term contracts with loyalty offers.</li><li><strong className="text-slate-900 dark:text-white">03.</strong> Review satisfaction and monthly-bill concerns in outreach.</li></ol></Card><RecentPredictionsTable rows={history} /></div>

    <Card title="Model drift monitoring" subtitle="How closely production signals match the training baseline"><div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl bg-emerald-50/80 p-5 dark:bg-emerald-400/10"><div><p className="text-lg font-semibold text-emerald-900 dark:text-emerald-100">{healthQuery.data?.model?.drift_detected ? 'Review required' : 'Excellent'}</p><p className="mt-1 text-sm text-emerald-800/80 dark:text-emerald-200/80">{healthQuery.data?.model?.drift_detected ? 'A production signal differs from the training baseline.' : 'No significant drift detected. Production data closely matches the training baseline.'}</p></div><div className="rounded-xl bg-white/80 px-4 py-3 text-right dark:bg-slate-900/60"><p className="text-xs uppercase tracking-wider text-slate-500">Current score</p><p className="text-xl font-semibold text-slate-950 dark:text-white">{healthQuery.data?.model?.drift_score?.toFixed?.(3) ?? 'Not Available'}</p></div></div></Card>
  </div>
}
