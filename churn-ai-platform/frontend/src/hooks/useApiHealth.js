import { useQuery } from '@tanstack/react-query'
import { getHealth } from '@/services/dashboardService'

export function useApiHealth() {
  return useQuery({
    queryKey: ['api-health'],
    queryFn: getHealth,
    refetchInterval: 30000,
    retry: 1,
  })
}
