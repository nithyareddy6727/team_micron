import MockAdapter from 'axios-mock-adapter'

import API, { fetchCustomers, fetchMetrics } from '@/core/api'

describe('API integration layer', () => {
  let mock

  beforeEach(() => {
    mock = new MockAdapter(API)
  })

  afterEach(() => {
    mock.restore()
  })

  it('unwraps strict envelope for customers', async () => {
    mock.onGet('/customers').reply(200, {
      success: true,
      data: {
        total: 1,
        limit: 100,
        offset: 0,
        customers: [
          {
            customer_id: 'cust_1',
            name: 'User One',
            email: 'u1@example.com',
            age: 30,
            gender: 'Male',
            tenure: 5,
            monthly_charges: 49.5,
            contract_type: 'Month-to-month',
          },
        ],
      },
      error: null,
    })

    const result = await fetchCustomers()
    expect(result.total).toBe(1)
    expect(result.customers[0].customer_id).toBe('cust_1')
  })

  it('throws on invalid envelope', async () => {
    mock.onGet('/metrics/app').reply(200, {
      success: false,
      data: {},
      error: 'contract broken',
    })

    await expect(fetchMetrics()).rejects.toThrow('contract broken')
  })
})
