import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../../../../core/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() },
}))

describe('catalogoService', () => {
  let api, mod

  beforeAll(async () => {
    api = (await import('../../../../core/api')).default
    mod = await import('../../../../features/catalogo/services/catalogoService')
  })

  beforeEach(() => vi.clearAllMocks())

  it('getTorres', async () => {
    api.get.mockResolvedValue({ data: [{ id: 1, nombre: 'IA' }] })
    const result = await mod.getTorres()
    expect(api.get).toHaveBeenCalledWith('/catalogo/torres')
    expect(result).toEqual([{ id: 1, nombre: 'IA' }])
  })

  it('createTorre', async () => {
    api.post.mockResolvedValue({ data: { id: 2 } })
    const result = await mod.createTorre('DevOps')
    expect(api.post).toHaveBeenCalledWith('/catalogo/torres', { nombre: 'DevOps' })
    expect(result).toEqual({ id: 2 })
  })

  it('deleteTorre', async () => {
    api.delete.mockResolvedValue({})
    await mod.deleteTorre(5)
    expect(api.delete).toHaveBeenCalledWith('/catalogo/torres/5')
  })

  it('getPerfiles without torreId', async () => {
    api.get.mockResolvedValue({ data: [{ id: 1, perfil: 'Java' }] })
    const result = await mod.getPerfiles()
    expect(api.get).toHaveBeenCalledWith('/catalogo/perfiles', { params: {} })
    expect(result).toEqual([{ id: 1, perfil: 'Java' }])
  })

  it('getPerfiles with torreId', async () => {
    api.get.mockResolvedValue({ data: [] })
    await mod.getPerfiles(3)
    expect(api.get).toHaveBeenCalledWith('/catalogo/perfiles', { params: { torre_id: 3 } })
  })

  it('createPerfil', async () => {
    api.post.mockResolvedValue({ data: { id: 10 } })
    const result = await mod.createPerfil({ perfil: 'Node', torre_id: 1 })
    expect(api.post).toHaveBeenCalledWith('/catalogo/perfiles', { perfil: 'Node', torre_id: 1 })
    expect(result).toEqual({ id: 10 })
  })

  it('updatePerfil', async () => {
    api.put.mockResolvedValue({ data: { id: 10, perfil: 'Node Senior' } })
    const result = await mod.updatePerfil(10, { perfil: 'Node Senior' })
    expect(api.put).toHaveBeenCalledWith('/catalogo/perfiles/10', { perfil: 'Node Senior' })
    expect(result).toEqual({ id: 10, perfil: 'Node Senior' })
  })

  it('deletePerfil', async () => {
    api.delete.mockResolvedValue({})
    await mod.deletePerfil(10)
    expect(api.delete).toHaveBeenCalledWith('/catalogo/perfiles/10')
  })

  it('getConsideraciones without torreId', async () => {
    api.get.mockResolvedValue({ data: ['c1'] })
    const result = await mod.getConsideraciones()
    expect(api.get).toHaveBeenCalledWith('/catalogo/consideraciones', { params: {} })
    expect(result).toEqual(['c1'])
  })

  it('createConsideracion', async () => {
    api.post.mockResolvedValue({ data: { id: 1 } })
    await mod.createConsideracion({ texto: 'test' })
    expect(api.post).toHaveBeenCalledWith('/catalogo/consideraciones', { texto: 'test' })
  })

  it('updateConsideracion', async () => {
    api.put.mockResolvedValue({ data: { id: 1 } })
    await mod.updateConsideracion(1, { texto: 'updated' })
    expect(api.put).toHaveBeenCalledWith('/catalogo/consideraciones/1', { texto: 'updated' })
  })

  it('deleteConsideracion', async () => {
    api.delete.mockResolvedValue({})
    await mod.deleteConsideracion(1)
    expect(api.delete).toHaveBeenCalledWith('/catalogo/consideraciones/1')
  })

  it('getEntregables', async () => {
    api.get.mockResolvedValue({ data: [{ torre: 'IA', items: ['doc'] }] })
    const result = await mod.getEntregables(2)
    expect(api.get).toHaveBeenCalledWith('/catalogo/entregables', { params: { torre_id: 2 } })
    expect(result).toEqual([{ torre: 'IA', items: ['doc'] }])
  })

  it('createEntregable', async () => {
    api.post.mockResolvedValue({ data: { id: 5 } })
    await mod.createEntregable({ torre_id: 1, items: ['x'] })
    expect(api.post).toHaveBeenCalledWith('/catalogo/entregables', { torre_id: 1, items: ['x'] })
  })

  it('updateEntregable', async () => {
    api.put.mockResolvedValue({ data: { id: 5 } })
    await mod.updateEntregable(5, { items: ['y'] })
    expect(api.put).toHaveBeenCalledWith('/catalogo/entregables/5', { items: ['y'] })
  })

  it('deleteEntregable', async () => {
    api.delete.mockResolvedValue({})
    await mod.deleteEntregable(5)
    expect(api.delete).toHaveBeenCalledWith('/catalogo/entregables/5')
  })

  it('getFueraAlcance', async () => {
    api.get.mockResolvedValue({ data: ['fda1'] })
    const result = await mod.getFueraAlcance()
    expect(api.get).toHaveBeenCalledWith('/catalogo/fuera-del-alcance', { params: {} })
    expect(result).toEqual(['fda1'])
  })

  it('createFueraAlcance', async () => {
    api.post.mockResolvedValue({ data: { id: 1 } })
    await mod.createFueraAlcance({ texto: 'test' })
    expect(api.post).toHaveBeenCalledWith('/catalogo/fuera-del-alcance', { texto: 'test' })
  })

  it('updateFueraAlcance', async () => {
    api.put.mockResolvedValue({ data: { id: 1 } })
    await mod.updateFueraAlcance(1, { texto: 'updated' })
    expect(api.put).toHaveBeenCalledWith('/catalogo/fuera-del-alcance/1', { texto: 'updated' })
  })

  it('deleteFueraAlcance', async () => {
    api.delete.mockResolvedValue({})
    await mod.deleteFueraAlcance(1)
    expect(api.delete).toHaveBeenCalledWith('/catalogo/fuera-del-alcance/1')
  })
})