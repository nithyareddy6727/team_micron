import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, Filter, Search, ShieldAlert, ShieldCheck, Sparkles, Zap } from 'lucide-react'
import { Card } from '@/components/ui/Card'
import { ErrorState } from '@/components/ui/ErrorState'
import { Input } from '@/components/ui/Input'
import { Skeleton } from '@/components/ui/Skeleton'
import { getAllCustomers } from '@/services/customerService'
import { useAppStore } from '@/hooks/useAppStore'
import { formatPercent, toRiskTone } from '@/utils/formatters'

const PAGE_SIZE = 25

const tones = {
  low: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300',
  medium: 'bg-amber-50 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300',
  high: 'bg-rose-50 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300',
}

export default function CustomersPage() {
  const [search, setSearch] = useState('')
  const [risk, setRisk] = useState('all')
  const [page, setPage] = useState(1)

  const sector = useAppStore((state) => state.sector) || 'telecom'

  const customersQuery = useQuery({
    queryKey: ['customers-page', search, risk, sector],
    queryFn: () => getAllCustomers({ search, risk_level: risk !== 'all' ? risk : undefined, sector }),
  })

  const filtered = useMemo(() => {
    const list = customersQuery.data?.customers || []
    return list.filter((row) => {
      const tone = toRiskTone(row.risk_level || row.risk)
      return risk === 'all' || tone === risk
    })
  }, [customersQuery.data, risk])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pagedRows = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const sectorLabels = {
    saas: {
      tenure: 'Account Age',
      charges: 'MRR ($)',
      customer: 'Account / Tenant',
    },
    consumer: {
      tenure: 'Membership Months',
      charges: 'Monthly Spend ($)',
      customer: 'Consumer / Member',
    },
    telecom: {
      tenure: 'Tenure (Mos)',
      charges: 'Monthly Bill ($)',
      customer: 'Subscriber',
    },
  }[sector] || {
    tenure: 'Tenure (Mos)',
    charges: 'Monthly Bill ($)',
    customer: 'Customer',
  }

  const highRiskCount = useMemo(() => {
    const list = customersQuery.data?.customers || []
    return list.filter((r) => toRiskTone(r.risk_level || r.risk) === 'high').length
  }, [customersQuery.data])

  return (
    <div className="space-y-4">
      <Card
        title="Customer Intelligence & Risk Explorer"
        subtitle={`Prioritize customer retention workflows under ${sector.toUpperCase()} profile`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-1 flex-wrap items-center gap-2 min-w-[280px]">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="absolute left-3.5 top-3 text-[#6f7691]" size={16} />
              <Input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value)
                  setPage(1)
                }}
                placeholder="Search by ID, name, or email..."
                className="pl-10"
              />
            </div>
          </div>

          {/* Quick Risk Filters */}
          <div className="flex flex-wrap items-center gap-1.5 rounded-2xl border border-slate-200 bg-slate-50 p-1 dark:border-slate-800 dark:bg-slate-900">
            <button
              onClick={() => {
                setRisk('all')
                setPage(1)
              }}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                risk === 'all'
                  ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-800 dark:text-white'
                  : 'text-slate-600 hover:text-slate-900 dark:text-slate-400'
              }`}
            >
              All Records
            </button>
            <button
              onClick={() => {
                setRisk('high')
                setPage(1)
              }}
              className={`inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-xs font-bold transition ${
                risk === 'high'
                  ? 'bg-rose-600 text-white shadow-sm'
                  : 'text-rose-700 hover:bg-rose-50 dark:text-rose-400 dark:hover:bg-rose-950/40'
              }`}
            >
              <ShieldAlert size={13} /> High Risk ({highRiskCount})
            </button>
            <button
              onClick={() => {
                setRisk('medium')
                setPage(1)
              }}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                risk === 'medium'
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'text-amber-700 hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-950/40'
              }`}
            >
              Medium Risk
            </button>
            <button
              onClick={() => {
                setRisk('low')
                setPage(1)
              }}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                risk === 'low'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-emerald-700 hover:bg-emerald-50 dark:text-emerald-400 dark:hover:bg-emerald-950/40'
              }`}
            >
              Low Risk
            </button>
          </div>
        </div>
      </Card>

      <Card
        title="Customer Intelligence Records"
        subtitle={`Showing ${filtered.length} customers ${risk !== 'all' ? `filtered by ${risk.toUpperCase()} risk` : ''}`}
      >
        {customersQuery.isLoading ? <Skeleton className="h-[460px]" /> : null}
        {customersQuery.isError ? (
          <ErrorState
            description={customersQuery.error.message}
            onRetry={customersQuery.refetch}
            actionLabel="Retry customers"
          />
        ) : null}
        {!customersQuery.isLoading && !customersQuery.isError ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs font-bold uppercase tracking-wider text-[#69708b] dark:border-slate-700 dark:text-slate-400">
                  <th className="py-3 pr-3">Customer ID</th>
                  <th className="py-3 pr-3">Name</th>
                  <th className="py-3 pr-3">{sectorLabels.tenure}</th>
                  <th className="py-3 pr-3">{sectorLabels.charges}</th>
                  <th className="py-3 pr-3">Risk Tier</th>
                  <th className="py-3 pr-3">Churn Probability</th>
                  <th className="py-3 pr-3">Primary Churn Driver</th>
                  <th className="py-3 pr-3">Recommended Retention Action</th>
                  <th className="py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {pagedRows.map((row) => {
                  const tone = toRiskTone(row.risk_level || row.risk)
                  const prob = row.prediction_probability || row.probability || 0
                  return (
                    <tr
                      key={row.customer_id}
                      className={`transition ${
                        tone === 'high' ? 'hover:bg-rose-50/40 dark:hover:bg-rose-950/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                      }`}
                    >
                      <td className="py-3.5 pr-3 font-mono font-semibold text-[#1D1D1F] dark:text-white">
                        {row.customer_id}
                      </td>
                      <td className="py-3.5 pr-3 text-slate-800 dark:text-slate-200">
                        {row.name || '--'}
                      </td>
                      <td className="py-3.5 pr-3 text-slate-600 dark:text-slate-400">
                        {row.tenure ?? '--'} mos
                      </td>
                      <td className="py-3.5 pr-3 font-medium text-slate-800 dark:text-slate-200">
                        ${Number(row.monthly_charges || 0).toFixed(2)}
                      </td>
                      <td className="py-3.5 pr-3">
                        <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${tones[tone]}`}>
                          {String(row.risk_level || row.risk || tone).toUpperCase()}
                        </span>
                      </td>
                      <td className="py-3.5 pr-3 font-bold text-[#1D1D1F] dark:text-white">
                        {formatPercent(prob)}
                      </td>
                      <td className="py-3.5 pr-3 text-xs font-medium text-slate-700 dark:text-slate-300">
                        <span className="inline-flex items-center gap-1">
                          <Zap size={12} className={tone === 'high' ? 'text-rose-500' : 'text-amber-500'} />
                          {row.primary_driver || 'Tenure & Cost Sensitivity'}
                        </span>
                      </td>
                      <td className="py-3.5 pr-3 text-xs text-slate-600 dark:text-slate-300">
                        {row.recommended_action || 'Review customer satisfaction at renewal.'}
                      </td>
                      <td className="py-3.5 text-right">
                        <a
                          href={`/prediction`}
                          className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:bg-[#0A84FF] hover:text-white dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-[#0A84FF]"
                        >
                          Predict <ArrowRight size={12} />
                        </a>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : null}

        {!customersQuery.isLoading && !customersQuery.isError ? (
          <div className="mt-4 flex items-center justify-between text-xs text-[#5f6475] dark:text-slate-400">
            <span>
              Page {page} of {totalPages} ({filtered.length} total accounts)
            </span>
            <div className="space-x-2">
              <button
                className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 font-medium disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900"
                onClick={() => setPage((value) => Math.max(1, value - 1))}
                disabled={page === 1}
              >
                Previous
              </button>
              <button
                className="rounded-xl border border-slate-300 bg-white px-3 py-1.5 font-medium disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900"
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
                disabled={page >= totalPages}
              >
                Next
              </button>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  )
}
