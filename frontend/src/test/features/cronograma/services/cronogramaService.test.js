import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../../../../core/api', () => ({
  default: { post: vi.fn() },
}))

describe('cronogramaService', () => {
  let api, mod

  beforeAll(async () => {
    api = (await import('../../../../core/api')).default
    mod = await import('../../../../features/cronograma/services/cronogramaService')
  })

  beforeEach(() => vi.clearAllMocks())

  it('generarCronograma should post to /cronograma/generar', async () => {
    api.post.mockResolvedValue({ data: { filename: 'cronograma.xlsx', content_b64: 'abc' } })
    const payload = { filial: 'corp', torres: ['IA'] }
    const result = await mod.generarCronograma(payload)
    expect(api.post).toHaveBeenCalledWith('/cronograma/generar', payload)
    expect(result).toEqual({ filename: 'cronograma.xlsx', content_b64: 'abc' })
  })
})