import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card } from '@/components/ui/Card'
import { ErrorState } from '@/components/ui/ErrorState'
import { Skeleton } from '@/components/ui/Skeleton'
import { TrendChart } from '@/components/charts/TrendChart'
import { getAllHistory } from '@/services/historyService'
import { formatDateTime, formatPercent, toRiskTone } from '@/utils/formatters'

const PAGE_SIZE = 25

const toneStyles = {
  low: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  medium: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  high: 'bg-rose-50 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
}

export default function HistoryPage() {
  const [risk, setRisk] = useState('all')
  const [page, setPage] = useState(1)

  const historyQuery = useQuery({
    queryKey: ['history-page'],
    queryFn: getAllHistory,
  })

  const filtered = useMemo(() => {
    const rows = historyQuery.data || []
    return rows.filter((item) => {
      const tone = toRiskTone(item.risk_level || item.risk)
      return risk === 'all' || tone === risk
    })
  }, [historyQuery.data, risk])

  const trendData = useMemo(
    () =>
      filtered.slice(-40).map((item, index) => ({
        hour: `${index + 1}`,
        prediction_count: Number(item.probability || 0) * 100,
      })),
    [filtered],
  )

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pagedRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <div className="space-y-4">
      <Card title="History Controls" subtitle="Filter prediction events by risk level">
        <div className="grid gap-3 md:grid-cols-[220px_auto]">
          <select
            className="rounded-2xl border border-[#d8deee] bg-white/90 px-4 py-2.5 text-sm text-[#1D1D1F] outline-none focus:border-[#0A84FF] dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            value={risk}
            onChange={(event) => {
              setRisk(event.target.value)
              setPage(1)
            }}
          >
            <option value="all">All risk levels</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <p className="self-center text-sm text-[#5f6475] dark:text-slate-400">Total rows: {filtered.length}</p>
        </div>
      </Card>

      <Card title="Prediction Trend" subtitle="Probability movement over recent events">
        <TrendChart data={trendData} />
      </Card>

      <Card title="History Events" subtitle="Full inference event trail">
        {historyQuery.isLoading ? <Skeleton className="h-[460px]" /> : null}
        {historyQuery.isError ? <ErrorState description={historyQuery.error.message} onRetry={historyQuery.refetch} actionLabel="Retry history" /> : null}

        {!historyQuery.isLoading && !historyQuery.isError ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200/90 text-[#69708b] dark:border-slate-700 dark:text-slate-400">
                  <th className="py-3 pr-3">Customer</th>
                  <th className="py-3 pr-3">Prediction</th>
                  <th className="py-3 pr-3">Probability</th>
                  <th className="py-3 pr-3">Confidence</th>
                  <th className="py-3 pr-3">Latency</th>
                  <th className="py-3 pr-3">Risk</th>
                  <th className="py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {pagedRows.map((row) => {
                  const tone = toRiskTone(row.risk_level || row.risk)
                  return (
                    <tr key={`${row.customer_id}-${row.timestamp}`} className="border-b border-slate-100 text-[#22252f] dark:border-slate-800 dark:text-slate-200">
                      <td className="py-3 pr-3">{row.customer_id}</td>
                      <td className="py-3 pr-3">{Number(row.prediction) === 1 ? 'Churn' : 'Not Churn'}</td>
                      <td className="py-3 pr-3">{formatPercent(row.probability)}</td>
                      <td className="py-3 pr-3">{formatPercent(row.confidence_score || row.confidence)}</td>
                      <td className="py-3 pr-3">{Number(row.latency_ms || row.latency || 0).toFixed(1)} ms</td>
                      <td className="py-3 pr-3"><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${toneStyles[tone]}`}>{String(row.risk_level || row.risk || tone).toUpperCase()}</span></td>
                      <td className="py-3">{formatDateTime(row.timestamp)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        {!historyQuery.isLoading && !historyQuery.isError ? (
          <div className="mt-4 flex items-center justify-between text-sm text-[#5f6475] dark:text-slate-400">
            <span>Page {page} of {totalPages}</span>
            <div className="space-x-2">
              <button className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page === 1}>Prev</button>
              <button className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900" onClick={() => setPage((value) => Math.min(totalPages, value + 1))} disabled={page === totalPages}>Next</button>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  )
}
