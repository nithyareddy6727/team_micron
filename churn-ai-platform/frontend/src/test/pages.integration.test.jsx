import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MockAdapter from 'axios-mock-adapter'

import DashboardPage from '@/pages/DashboardPage'
import PredictionPage from '@/pages/PredictionPage'
import SettingsPage from '@/pages/SettingsPage'
import apiClient from '@/services/apiClient'
import { useAppStore } from '@/hooks/useAppStore'

vi.mock('@/components/PowerBI/PowerBIReport', () => ({
  PowerBIReport: () => <div data-testid="powerbi-report">Power BI mock</div>,
}))

function renderWithClient(ui) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
        retry: false,
      },
    },
  })

  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>)
}

describe('Dashboard page workflow', () => {
  let mock

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    useAppStore.setState({
      user: { name: 'Admin', role: 'admin' },
      apiBaseUrl: 'http://127.0.0.1:8000',
      latestPrediction: null,
      predictionHistory: [],
    })
  })

  afterEach(() => {
    mock.restore()
  })

  it('renders KPI metrics and recent history from backend contracts', async () => {
    mock.onGet('/dashboard').reply(200, {
      success: true,
      data: {
        total_customers: 7043,
        total_predictions: 100,
        churn_rate: 0.213,
        high_risk_count: 24,
        high_risk_percentage: 24,
        risk_distribution: { low: 50, medium: 26, high: 24 },
        prediction_trend: [{ hour: '1', prediction_count: 8 }],
      },
      error: null,
    })

    mock.onGet('/history').reply(200, {
      success: true,
      data: {
        total: 1,
        limit: 8,
        offset: 0,
        history: [
          {
            customer_id: 'CUST-1001',
            risk_level: 'High',
            probability: 0.84,
            latency_ms: 22.1,
            timestamp: '2026-04-06T10:00:00Z',
          },
        ],
      },
      error: null,
    })

    renderWithClient(<DashboardPage />)

    expect(await screen.findByText('Total customers')).toBeInTheDocument()
    expect(screen.getByText('7,043')).toBeInTheDocument()
    expect(screen.getByText('Recent predictions')).toBeInTheDocument()
    expect(await screen.findByText('CUST-1001')).toBeInTheDocument()
  })
})

describe('Prediction page workflow', () => {
  let mock

  beforeEach(() => {
    mock = new MockAdapter(apiClient)
    useAppStore.setState({
      user: { name: 'Admin', role: 'admin' },
      apiBaseUrl: 'http://127.0.0.1:8000',
      latestPrediction: null,
      predictionHistory: [],
    })
  })

  afterEach(() => {
    mock.restore()
  })

  it('submits JSON payload and renders churn probability', async () => {
    mock.onGet('/customers').reply(200, {
      success: true,
      data: {
        total: 1,
        limit: 250,
        offset: 0,
        customers: [{ customer_id: 'CUST-1001', name: 'Live Customer' }],
      },
      error: null,
    })

    mock.onPost('/predict').reply(200, {
      success: true,
      data: {
        prediction: 1,
        probability: 0.91,
        risk_level: 'High',
        confidence_score: 0.9,
        latency_ms: 19.7,
        model_version: 'v2',
        explanation_text: 'Customer has high churn propensity.',
        top_features: [],
      },
      error: null,
    })

    const user = userEvent.setup()
    renderWithClient(<PredictionPage />)

    await user.click(await screen.findByRole('button', { name: 'Predict Churn' }))

    expect(await screen.findByText('Prediction Output')).toBeInTheDocument()
    expect(await screen.findByText('Churn')).toBeInTheDocument()
    expect(await screen.findByText('91.0%')).toBeInTheDocument()
  })
})

describe('Settings page workflow', () => {
  beforeEach(() => {
    useAppStore.setState({
      user: { name: 'Admin', role: 'admin' },
      apiBaseUrl: 'http://127.0.0.1:8000',
    })
  })

  it('updates runtime API URL from settings form', async () => {
    const user = userEvent.setup()
    renderWithClient(<SettingsPage />)

    const input = await screen.findByPlaceholderText('http://127.0.0.1:8000')
    await user.clear(input)
    await user.type(input, 'http://localhost:9000')

    await user.click(screen.getByRole('button', { name: 'Save API URL' }))

    await waitFor(() => {
      expect(useAppStore.getState().apiBaseUrl).toBe('http://localhost:9000')
    })

    expect(await screen.findByText('API base URL updated. Data queries were refreshed.')).toBeInTheDocument()
    expect(screen.getByTestId('powerbi-report')).toBeInTheDocument()
  })
})
