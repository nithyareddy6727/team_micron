import { create } from 'zustand'

const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

const getPreferredTheme = () => {
  const saved = localStorage.getItem('churnx-theme')
  if (saved === 'light' || saved === 'dark') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const DEFAULT_USER = {
  name: 'Admin',
  role: 'ML Engineer',
}

export const useAppStore = create((set) => ({
  user: DEFAULT_USER,
  theme: getPreferredTheme(),
  apiBaseUrl: DEFAULT_API_BASE_URL,
  latestPrediction: null,
  predictionHistory: [],
  sector: localStorage.getItem('churnx-sector') || 'telecom',
  setSector: (sector) => {
    localStorage.setItem('churnx-sector', sector)
    set({ sector })
  },
  setTheme: (theme) => {
    localStorage.setItem('churnx-theme', theme)
    set({ theme })
  },
  setApiBaseUrl: (apiBaseUrl) => set({ apiBaseUrl }),
  setLatestPrediction: (prediction) =>
    set((state) => ({
      latestPrediction: prediction,
      predictionHistory: [prediction, ...state.predictionHistory].slice(0, 12),
    })),
}))
