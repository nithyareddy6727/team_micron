import { createElement } from 'react'
import { TrendingUp } from 'lucide-react'
import { Card } from '@/components/ui/Card'

export function KpiCard({ label, value, icon, tone = 'blue', detail = 'Live API metric', sparkline = [] }) {
  const color = tone === 'rose' ? 'text-rose-600 bg-rose-100 dark:bg-rose-400/15 dark:text-rose-300' : tone === 'emerald' ? 'text-emerald-600 bg-emerald-100 dark:bg-emerald-400/15 dark:text-emerald-300' : 'text-blue-600 bg-blue-100 dark:bg-blue-400/15 dark:text-blue-300'
  const points = sparkline.length ? sparkline.map((v, index) => `${(index / Math.max(sparkline.length - 1, 1)) * 100},${30 - (v / Math.max(...sparkline, 1)) * 24}`).join(' ') : ''
  return <Card className="group min-h-40 overflow-hidden transition duration-200 hover:-translate-y-1 hover:shadow-[0_22px_45px_rgba(34,59,112,0.15)]"><div className="flex items-start justify-between"><div className={`flex h-10 w-10 items-center justify-center rounded-xl ${color}`}>{createElement(icon, { size: 19 })}</div>{points ? <svg className="h-9 w-20" viewBox="0 0 100 32" aria-label={`${label} trend`} role="img"><polyline points={points} fill="none" stroke="currentColor" strokeWidth="2.5" className="text-blue-500" /></svg> : null}</div><p className="mt-5 text-xs font-medium uppercase tracking-[0.13em] text-slate-500">{label}</p><p className="mt-1 text-2xl font-semibold tracking-tight text-slate-950 dark:text-white">{value}</p><p className="mt-2 flex items-center gap-1 text-xs text-slate-500"><TrendingUp size={13} className="text-emerald-500" />{detail}</p></Card>
}
