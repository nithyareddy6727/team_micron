import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { QueryState } from '@/shared/UI'

describe('QueryState', () => {
  it('renders skeleton for loading state', () => {
    render(<QueryState isLoading isError={false} error={null} onRetry={() => {}} />)
    const skeleton = document.querySelector('.skeleton-shimmer')
    expect(skeleton).toBeInTheDocument()
  })

  it('renders error and retry action', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(
      <QueryState
        isLoading={false}
        isError
        error={new Error('Boom')}
        onRetry={onRetry}
      />,
    )

    expect(screen.getByText('Request failed')).toBeInTheDocument()
    expect(screen.getByText('Boom')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })
})
