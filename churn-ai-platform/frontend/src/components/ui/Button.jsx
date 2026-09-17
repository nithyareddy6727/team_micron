import { cn } from '@/utils/cn'

const base =
  'inline-flex items-center justify-center rounded-2xl px-4 py-2.5 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2'

const variants = {
  primary: 'bg-[#0A84FF] text-white shadow-[0_12px_24px_rgba(10,132,255,0.28)] hover:bg-[#0676e5] focus-visible:ring-[#0A84FF]',
  ghost: 'bg-white/65 text-[#1D1D1F] backdrop-blur-md hover:bg-white/90 focus-visible:ring-[#0A84FF]',
  subtle: 'bg-[#f0f4ff] text-[#25518f] hover:bg-[#e5eeff] focus-visible:ring-[#0A84FF]',
}

export function Button({ className, variant = 'primary', type = 'button', ...props }) {
  return <button type={type} className={cn(base, variants[variant], className)} {...props} />
}
