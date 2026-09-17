import { create } from 'zustand'
import { DEFAULT_API_BASE_URL } from '@/core/config'

const persistedTheme = localStorage.getItem('churnx-theme') || 'dark'

export const useStore = create((set) => ({
  theme: persistedTheme,
  apiBaseUrl: DEFAULT_API_BASE_URL,
  notificationsEnabled: true,
  refreshInterval: 30000,
  searchTerm: '',
  setTheme: (theme) => {
    localStorage.setItem('churnx-theme', theme)
    set({ theme })
  },
  setApiBaseUrl: (apiBaseUrl) => set({ apiBaseUrl }),
  setNotificationsEnabled: (notificationsEnabled) => set({ notificationsEnabled }),
  setRefreshInterval: (refreshInterval) => set({ refreshInterval }),
  setSearchTerm: (searchTerm) => set({ searchTerm }),
}))
