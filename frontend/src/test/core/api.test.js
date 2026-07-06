import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('API Error Interceptor', () => {
  let api

  beforeEach(async () => {
    vi.resetModules()
    api = (await import('../../core/api')).default
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should create an axios instance with correct baseURL', () => {
    expect(api.defaults.baseURL).toBe('/api/v1')
    expect(api.defaults.headers['Content-Type']).toBe('application/json')
  })

  it('should reject with extracted detail string from response', async () => {
    const error = {
      response: {
        data: { detail: 'Error de prueba' },
      },
      message: 'Request failed',
    }

    await expect(api.interceptors.response.handlers[0].rejected(error)).rejects.toThrow('Error de prueba')
  })

  it('should join Pydantic validation errors from detail array', async () => {
    const error = {
      response: {
        data: {
          detail: [
            { loc: ['body', 'name'], msg: 'field required' },
            { loc: ['body', 'email'], msg: 'invalid email' },
          ],
        },
      },
      message: 'Request failed',
    }

    await expect(api.interceptors.response.handlers[0].rejected(error)).rejects.toThrow(
      'name: field required. email: invalid email'
    )
  })

  it('should stringify object detail', async () => {
    const error = {
      response: {
        data: { detail: { foo: 'bar' } },
      },
      message: 'Request failed',
    }

    await expect(api.interceptors.response.handlers[0].rejected(error)).rejects.toThrow('{"foo":"bar"}')
  })

  it('should fall back to the error message when object detail cannot be stringified', async () => {
    const error = {
      response: {
        data: {
          detail: {
            toJSON: () => undefined,
          },
        },
      },
      message: 'Request failed',
    }

    await expect(api.interceptors.response.handlers[0].rejected(error)).rejects.toThrow('Request failed')
  })

  it('should fall back to default error message when detail is missing', async () => {
    const error = {
      response: {
        data: {},
      },
      message: 'Network Error',
    }

    // The fallback is 'Error desconocido' when detail is missing and msg evaluates to that
    await expect(api.interceptors.response.handlers[0].rejected(error)).rejects.toThrow('Error desconocido')
  })

  it('should handle missing response gracefully with default message', async () => {
    const error = { message: 'No response from server' }

    // Without response, msg remains 'Error desconocido', then falls back to err.message
    await expect(api.interceptors.response.handlers[0].rejected(error)).rejects.toThrow('Error desconocido')
  })
})