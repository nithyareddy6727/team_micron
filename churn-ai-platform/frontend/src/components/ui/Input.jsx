import { cn } from '@/utils/cn'

export function Input({ className, ...props }) {
  return (
    <input
      className={cn(
        'w-full rounded-2xl border border-[#d8deee] bg-white/90 px-4 py-2.5 text-sm text-[#1D1D1F] outline-none transition placeholder:text-[#6f7282] focus:border-[#0A84FF] focus:ring-2 focus:ring-[#0A84FF]/20',
        className,
      )}
      {...props}
    />
  )
}
