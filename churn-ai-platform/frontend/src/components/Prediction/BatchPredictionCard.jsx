import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export function BatchPredictionCard({
  batchFile,
  setBatchFile,
  submitBatch,
  isSubmitting,
  batchJobId,
  batchStatus,
  batchError,
}) {
  return (
    <Card title="Batch Prediction" subtitle="Upload CSV for asynchronous processing">
      <div className="space-y-3">
        <input
          type="file"
          accept=".csv"
          onChange={(event) => setBatchFile(event.target.files?.[0] || null)}
          className="block w-full text-sm text-[#4d5467] file:mr-4 file:rounded-2xl file:border-0 file:bg-[#0A84FF] file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-[#0676e5] dark:text-slate-300"
        />
        <div className="flex flex-wrap gap-2">
          <Button onClick={submitBatch} disabled={!batchFile || isSubmitting}>
            {isSubmitting ? 'Submitting batch...' : 'Submit CSV Batch'}
          </Button>
          {batchJobId ? (
            <span className="rounded-full bg-[#edf4ff] px-3 py-1 text-xs font-semibold text-[#244f8f] dark:bg-slate-800 dark:text-slate-300">
              Job: {batchJobId}
            </span>
          ) : null}
        </div>

        {batchStatus ? (
          <div className="rounded-2xl bg-white/85 p-3 text-sm dark:bg-slate-900/80">
            <p className="font-semibold text-[#1D1D1F] dark:text-white">Status: {batchStatus.status}</p>
            <p className="mt-1 text-[#5e667d] dark:text-slate-400">
              Processed {batchStatus.processed_rows}/{batchStatus.total_rows} | Success {batchStatus.successful_rows} | Failed {batchStatus.failed_rows}
            </p>
          </div>
        ) : null}

        {batchError ? <p className="text-sm text-rose-600 dark:text-rose-300">{batchError}</p> : null}
      </div>
    </Card>
  )
}
