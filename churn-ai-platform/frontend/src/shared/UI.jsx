export function Card({ title, subtitle, children, className = '' }) {
  return (
    <section className={`glass-panel rounded-2xl p-5 ${className}`}>
      {(title || subtitle) && (
        <header className="mb-4">
          {title && <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-300">{title}</h3>}
          {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  )
}

export function EmptyState({ title, description, actionLabel, onAction }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/20 bg-white/5 p-8 text-center">
      <h4 className="text-lg font-semibold text-white">{title}</h4>
      <p className="mt-2 text-sm text-slate-300">{description}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 rounded-lg border border-white/20 px-4 py-2 text-sm text-slate-100 hover:bg-white/10"
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}

export function Skeleton({ className = '' }) {
  return <div className={`skeleton-shimmer rounded-xl ${className}`} />
}

export function QueryState({ isLoading, isError, error, onRetry, loadingClassName = 'h-80' }) {
  if (isLoading) {
    return <Skeleton className={loadingClassName} />
  }

  if (isError) {
    return (
      <EmptyState
        title="Request failed"
        description={error?.message || 'Unexpected API error'}
        actionLabel="Retry"
        onAction={onRetry}
      />
    )
  }

  return null
}

const riskStyles = {
  high: 'bg-rose-500/20 text-rose-200 border-rose-400/40',
  medium: 'bg-amber-500/20 text-amber-100 border-amber-400/40',
  low: 'bg-emerald-500/20 text-emerald-100 border-emerald-400/40',
}

const riskLabels = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

export function RiskBadge({ risk = 'low' }) {
  return <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${riskStyles[risk]}`}>{riskLabels[risk]}</span>
}

export function ProgressBar({ value = 0 }) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className="h-2.5 w-full rounded-full bg-white/10">
      <div
        className="h-2.5 rounded-full bg-gradient-to-r from-indigo-500 via-fuchsia-500 to-cyan-400 transition-all duration-500"
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}

export function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative h-7 w-14 rounded-full transition ${checked ? 'bg-emerald-500' : 'bg-slate-500/60'}`}
    >
      <span
        className={`absolute top-0.5 h-6 w-6 rounded-full bg-white transition ${checked ? 'left-7' : 'left-0.5'}`}
      />
    </button>
  )
}
