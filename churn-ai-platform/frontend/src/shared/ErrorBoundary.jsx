import { Component } from 'react'
import { EmptyState } from '@/components/ui/EmptyState'

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    if (import.meta.env.DEV) {
      console.error('[error-boundary]', error, errorInfo)
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen p-6 text-[#1D1D1F] dark:text-slate-100">
          <div className="mx-auto max-w-3xl">
            <EmptyState
              title="Something went wrong"
              description="Please reload the workspace. Your data has not been changed."
              actionLabel="Reload"
              onAction={() => window.location.reload()}
            />
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
