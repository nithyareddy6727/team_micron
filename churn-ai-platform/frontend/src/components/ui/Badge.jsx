const tones = {
  low: 'border-emerald-400/30 bg-emerald-500/15 text-emerald-100',
  medium: 'border-amber-400/30 bg-amber-400/15 text-amber-100',
  high: 'border-rose-400/30 bg-rose-500/15 text-rose-100',
  neutral: 'border-slate-400/30 bg-slate-500/15 text-slate-100',
}

export function Badge({ tone = 'neutral', children, className = '' }) {
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${tones[tone] || tones.neutral} ${className}`}>
      {children}
    </span>
  )
}
