import { cn } from '@/utils/cn'

export function Card({ title, subtitle, actions, className, children }) {
  return (
    <section
      className={cn(
        'rounded-3xl border border-white/60 bg-white/72 p-5 shadow-[0_18px_45px_rgba(34,59,112,0.08)] backdrop-blur-xl dark:border-slate-700 dark:bg-slate-900/65',
        className,
      )}
    >
      {(title || subtitle || actions) && (
        <header className="mb-4 flex items-start justify-between gap-4">
          <div>
            {title ? <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-[#25272d] dark:text-slate-100">{title}</h3> : null}
            {subtitle ? <p className="mt-1 text-sm text-[#666a77] dark:text-slate-400">{subtitle}</p> : null}
          </div>
          {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
        </header>
      )}
      {children}
    </section>
  )
}
