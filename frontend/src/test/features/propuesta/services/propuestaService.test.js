import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../../../../core/api', () => ({
  default: { post: vi.fn(), get: vi.fn() },
}))

describe('propuestaService', () => {
  let api, mod

  beforeAll(async () => {
    api = (await import('../../../../core/api')).default
    mod = await import('../../../../features/propuesta/services/propuestaService')
  })

  beforeEach(() => vi.clearAllMocks())

  it('generarPropuesta should post to /propuesta/generar', async () => {
    api.post.mockResolvedValue({ data: { filename: 'test.pptx', content_b64: 'abc' } })
    const payload = { filial: 'corp', opciones: { perfiles: true }, torres_seleccionadas: ['IA'] }
    const result = await mod.generarPropuesta(payload)
    expect(api.post).toHaveBeenCalledWith('/propuesta/generar', payload)
    expect(result).toEqual({ filename: 'test.pptx', content_b64: 'abc' })
  })

  it('getPerfilesCatalog without torreId', async () => {
    api.get.mockResolvedValue({ data: [{ id: 1, perfil: 'Java' }] })
    const result = await mod.getPerfilesCatalog()
    expect(api.get).toHaveBeenCalledWith('/catalogo/perfiles', { params: {} })
    expect(result).toEqual([{ id: 1, perfil: 'Java' }])
  })

  it('getPerfilesCatalog with torreId', async () => {
    api.get.mockResolvedValue({ data: [] })
    await mod.getPerfilesCatalog(3)
    expect(api.get).toHaveBeenCalledWith('/catalogo/perfiles', { params: { torre_id: 3 } })
  })
})