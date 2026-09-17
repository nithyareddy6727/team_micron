import { Moon, Sun } from 'lucide-react'
import { motion } from 'framer-motion'
import { useAppStore } from '@/hooks/useAppStore'

export function ThemeToggle() {
  const theme = useAppStore((state) => state.theme)
  const setTheme = useAppStore((state) => state.setTheme)
  const dark = theme === 'dark'

  return (
    <button
      aria-label="Toggle dark mode"
      onClick={() => setTheme(dark ? 'light' : 'dark')}
      className="relative inline-flex h-10 w-[74px] items-center rounded-full border border-slate-300/70 bg-white/80 px-1 transition dark:border-slate-600 dark:bg-slate-800"
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 450, damping: 32 }}
        className="absolute left-1 top-1 inline-flex h-8 w-8 items-center justify-center rounded-full bg-[#0A84FF] text-white shadow"
        style={{ transform: `translateX(${dark ? 34 : 0}px)` }}
      >
        {dark ? <Moon size={15} /> : <Sun size={15} />}
      </motion.span>
      <span className="sr-only">Theme</span>
    </button>
  )
}
