import { QueryClient } from '@tanstack/react-query'
import { QUERY_DEFAULTS } from '@/core/config'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: QUERY_DEFAULTS,
  },
})