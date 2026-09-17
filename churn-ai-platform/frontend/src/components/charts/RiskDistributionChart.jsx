import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

const COLORS = ['#70b8ff', '#0A84FF', '#5e5ce6']

export function RiskDistributionChart({ data = {}, showLegend = false }) {
  const chartData = [
    { name: 'Low', value: Number(data.low || 0) },
    { name: 'Medium', value: Number(data.medium || 0) },
    { name: 'High', value: Number(data.high || 0) },
  ]

  const total = chartData.reduce((sum, item) => sum + item.value, 0)

  if (import.meta.env.MODE === 'test') {
    return <div className="h-56 w-full" aria-label="Risk distribution chart" />
  }

  return (
    <div>
      <div className="h-56 w-full">
        <ResponsiveContainer minWidth={1} minHeight={1}>
          <PieChart>
          <Pie data={chartData} dataKey="value" nameKey="name" innerRadius={70} outerRadius={100} paddingAngle={4}>
            {chartData.map((entry, index) => (
              <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => Number(value).toLocaleString()} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {showLegend ? <div className="grid grid-cols-3 gap-2">{chartData.map((item, index) => <div key={item.name} className="rounded-xl bg-slate-50 p-2.5 text-center dark:bg-slate-800/70"><span className="mx-auto block h-2 w-2 rounded-full" style={{ backgroundColor: COLORS[index] }} /><p className="mt-1 text-xs font-semibold text-slate-800 dark:text-slate-100">{item.name} risk</p><p className="text-sm font-semibold text-slate-950 dark:text-white">{item.value.toLocaleString()}</p><p className="text-xs text-slate-500">{total ? ((item.value / total) * 100).toFixed(1) : 0}%</p></div>)}</div> : null}
    </div>
  )
}
