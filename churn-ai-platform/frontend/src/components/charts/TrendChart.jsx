import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export function TrendChart({ data = [] }) {
  const safeData = Array.isArray(data) ? data : []

  if (!safeData.length) {
    return (
      <div className="flex h-72 items-center justify-center rounded-2xl border border-dashed border-slate-300/80 bg-white/80 text-sm text-slate-500 dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
        No trend data yet. Run more predictions to build a timeline.
      </div>
    )
  }

  if (import.meta.env.MODE === 'test') {
    return <div className="h-72 w-full" aria-label="Prediction trend chart" />
  }

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer minWidth={1} minHeight={1}>
        <AreaChart data={safeData} margin={{ left: 10, right: 10, top: 10, bottom: 0 }}>
          <defs>
            <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0A84FF" stopOpacity={0.45} />
              <stop offset="95%" stopColor="#5e5ce6" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#d7deeb" />
          <XAxis dataKey="hour" tick={{ fill: '#585c6b', fontSize: 12 }} />
          <YAxis tick={{ fill: '#585c6b', fontSize: 12 }} />
          <Tooltip formatter={(value) => [Number(value).toLocaleString(), 'Predictions']} labelFormatter={(label) => `Time: ${label}`} contentStyle={{ borderRadius: 12, border: '1px solid #d7deeb' }} />
          <Area type="monotone" dataKey="prediction_count" stroke="#0A84FF" strokeWidth={3} fill="url(#trendFill)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
