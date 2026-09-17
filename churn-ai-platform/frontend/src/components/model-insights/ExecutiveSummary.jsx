import { createElement } from 'react'
import { Activity, BadgeCheck, BrainCircuit, Database, ShieldCheck } from 'lucide-react'
import { Card } from '@/components/ui/Card'

const statusItems = [
  { label: 'API', value: 'Healthy', icon: Activity },
  { label: 'Prediction engine', value: 'Running', icon: BrainCircuit },
  { label: 'Database', value: 'Connected', icon: Database },
  { label: 'ML model', value: 'Loaded', icon: ShieldCheck },
]

export function ExecutiveSummary({ analytics, health }) {
  const modelReady = health?.system?.model_loaded
  const databaseReady = health?.system?.db_connected
  const apiReady = health?.system?.api_status === 'OK'
  const driftDetected = health?.model?.drift_detected
  const items = statusItems.map((item) => ({
    ...item,
    value: item.label === 'API' ? (apiReady ? 'Healthy' : 'Unavailable') : item.label === 'Database' ? (databaseReady ? 'Connected' : 'Unavailable') : item.label === 'ML model' ? (modelReady ? 'Loaded' : 'Unavailable') : (modelReady ? 'Running' : 'Unavailable'),
  }))

  return (
    <Card className="relative overflow-hidden border-blue-100/80 bg-gradient-to-br from-white/90 via-blue-50/75 to-indigo-50/85 dark:border-blue-900/50 dark:from-slate-900 dark:via-slate-900 dark:to-indigo-950/50">
      <div className="absolute -right-16 -top-20 h-64 w-64 rounded-full bg-blue-400/20 blur-3xl" />
      <div className="relative grid gap-6 xl:grid-cols-[1.1fr_1fr]">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-blue-700 dark:text-blue-300"><BadgeCheck size={18} /> EXECUTIVE SUMMARY</div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <h3 className="text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">Model health</h3>
            <span className={`rounded-full px-3 py-1 text-sm font-semibold ${driftDetected ? 'bg-amber-100 text-amber-800 dark:bg-amber-400/15 dark:text-amber-200' : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-200'}`}>{driftDetected ? 'Needs attention' : 'Healthy'}</span>
          </div>
          <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600 dark:text-slate-300">Live production signals are connected to the intelligence console. Metrics not supplied by the current API are clearly identified.</p>
          <dl className="mt-6 grid grid-cols-2 gap-x-6 gap-y-5 sm:grid-cols-4">
            <div><dt className="text-xs font-medium uppercase tracking-wider text-slate-500">Current model</dt><dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">Not Available</dd></div>
            <div><dt className="text-xs font-medium uppercase tracking-wider text-slate-500">Last training</dt><dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">Not Available</dd></div>
            <div><dt className="text-xs font-medium uppercase tracking-wider text-slate-500">Dataset size</dt><dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{Number(analytics?.total_customers || 0).toLocaleString()}</dd></div>
            <div><dt className="text-xs font-medium uppercase tracking-wider text-slate-500">Accuracy</dt><dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">Not Available</dd></div>
            <div><dt className="text-xs font-medium uppercase tracking-wider text-slate-500">ROC-AUC</dt><dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">Not Available</dd></div>
            <div><dt className="text-xs font-medium uppercase tracking-wider text-slate-500">Model drift</dt><dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{health?.model?.drift_score?.toFixed?.(3) ?? 'Not Available'}</dd></div>
            <div><dt className="text-xs font-medium uppercase tracking-wider text-slate-500">Prediction confidence</dt><dd className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">Not Available</dd></div>
            <div><dt className="text-xs font-medium uppercase tracking-wider text-slate-500">Explainability</dt><dd className="mt-1 text-lg font-semibold text-emerald-700 dark:text-emerald-300">Enabled</dd></div>
          </dl>
        </div>
        <div className="grid grid-cols-2 gap-3 self-end">
          {items.map(({ label, value, icon: Icon }) => <div key={label} className="rounded-2xl border border-white/80 bg-white/70 p-4 shadow-sm backdrop-blur dark:border-slate-700 dark:bg-slate-950/35">{createElement(Icon, { size: 18, className: value === 'Unavailable' ? 'text-slate-400' : 'text-emerald-500' })}<p className="mt-3 text-xs font-medium text-slate-500">{label}</p><p className="mt-1 text-sm font-semibold text-slate-900 dark:text-white">{value}</p></div>)}
        </div>
      </div>
    </Card>
  )
}
