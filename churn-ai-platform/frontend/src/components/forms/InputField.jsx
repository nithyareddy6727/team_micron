import { forwardRef } from 'react'

export const InputField = forwardRef(function InputField(
  { label, hint, className = '', containerClassName = '', ...props },
  ref,
) {
  return (
    <label className={`block ${containerClassName}`}>
      {label ? <span className="mb-2 block text-sm font-medium text-slate-200">{label}</span> : null}
      <input
        ref={ref}
        {...props}
        className={`w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300 focus:bg-white/7 ${className}`}
      />
      {hint ? <span className="mt-2 block text-xs text-slate-400">{hint}</span> : null}
    </label>
  )
})
