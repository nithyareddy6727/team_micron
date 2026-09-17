export function EmptyState({ title, description, actionLabel, onAction }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/15 bg-white/5 px-6 py-10 text-center">
      <h4 className="text-lg font-semibold text-white">{title}</h4>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-300">{description}</p>
      {actionLabel && onAction ? (
        <button
          type="button"
          onClick={onAction}
          className="mt-5 rounded-xl border border-white/15 bg-white/10 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/15"
        >
          {actionLabel}
        </button>
      ) : null}
    </div>
  )
}
