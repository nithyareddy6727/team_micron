import { Button } from '@/components/ui/Button'

export function ErrorState({ title = "We couldn't load this information", description, actionLabel = 'Try again', onRetry, onAction }) {
  const action = onRetry || onAction

  return (
    <div className="rounded-3xl border border-rose-200 bg-rose-50/90 px-6 py-10 text-center dark:border-rose-500/25 dark:bg-rose-500/10">
      <h4 className="text-lg font-semibold text-rose-700 dark:text-rose-100">{title}</h4>
      <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-rose-700/80 dark:text-rose-100/80">{description && !/error|failed|exception|api|http/i.test(description) ? description : "Please try again in a moment. If the problem continues, check that the service is available."}</p>
      {action ? (
        <Button type="button" onClick={action} variant="subtle" className="mt-5">
          {actionLabel}
        </Button>
      ) : null}
    </div>
  )
}
