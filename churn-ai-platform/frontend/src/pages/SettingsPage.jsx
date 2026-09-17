import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { PowerBIReport } from '@/components/PowerBI/PowerBIReport'
import { useAppStore } from '@/hooks/useAppStore'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const apiBaseUrl = useAppStore((state) => state.apiBaseUrl)
  const setApiBaseUrl = useAppStore((state) => state.setApiBaseUrl)

  const [draftApiUrl, setDraftApiUrl] = useState(apiBaseUrl)
  const [message, setMessage] = useState('')

  const saveMutation = useMutation({
    mutationFn: async () => {
      setApiBaseUrl(draftApiUrl.trim())
      await queryClient.invalidateQueries()
      return 'Saved'
    },
    onSuccess: () => {
      setMessage('API base URL updated. Data queries were refreshed.')
    },
    onError: (error) => {
      setMessage(error.message)
    },
  })

  return (
    <div className="space-y-5">
      <Card title="Backend Integration" subtitle="Configure API endpoint and connection behavior">
        <div className="grid gap-3 md:grid-cols-[1fr_auto]">
          <Input
            value={draftApiUrl}
            onChange={(event) => setDraftApiUrl(event.target.value)}
            placeholder="http://127.0.0.1:8000"
          />
          <Button onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
            {saveMutation.isPending ? 'Saving...' : 'Save API URL'}
          </Button>
        </div>
        {message ? <p className="mt-3 text-sm text-[#556081] dark:text-slate-300">{message}</p> : null}
        <p className="mt-3 text-xs text-[#6c7287] dark:text-slate-400">
          For production, use HTTPS and add VITE_API_KEY in the frontend environment for secured endpoint access.
        </p>
      </Card>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
        <Card title="Power BI Integration" subtitle="Embedded executive reporting panel">
        <div className="mb-3 rounded-2xl bg-[#eef4ff] p-3 text-xs text-[#39527d] dark:bg-slate-800 dark:text-slate-300">
          Configure backend token broker variables: POWERBI_TENANT_ID, POWERBI_CLIENT_ID,
          POWERBI_CLIENT_SECRET, POWERBI_WORKSPACE_ID, POWERBI_REPORT_ID, and POWERBI_EMBED_URL.
          Frontend-only VITE_POWERBI_* variables are fallback for local development only.
        </div>
        <PowerBIReport />
        </Card>
      </motion.div>
    </div>
  )
}
