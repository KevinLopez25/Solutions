import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../../../../core/api', () => ({
  default: {
    post: vi.fn(),
  },
}))

const api = (await import('../../../../core/api')).default

describe('aiService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('enviarMensajeIA should post to /ai/chat', async () => {
    api.post.mockResolvedValue({ data: { reply: 'ok' } })
    const mod = await import('../../../../features/ai/services/aiService')
    const result = await mod.enviarMensajeIA([{ role: 'user', content: 'hola' }])
    expect(api.post).toHaveBeenCalledWith('/ai/chat', { messages: [{ role: 'user', content: 'hola' }] })
    expect(result).toEqual({ reply: 'ok' })
  })

  it('modificarPropuesta should post to /ai/modificar-propuesta', async () => {
    api.post.mockResolvedValue({ data: { filename: 'test.pptx' } })
    const mod = await import('../../../../features/ai/services/aiService')
    const result = await mod.modificarPropuesta({ content_b64: 'abc' })
    expect(api.post).toHaveBeenCalledWith('/ai/modificar-propuesta', { content_b64: 'abc' })
    expect(result).toEqual({ filename: 'test.pptx' })
  })

  it('reemplazarLogo should post to /ai/reemplazar-logo', async () => {
    api.post.mockResolvedValue({ data: { content_b64: 'new' } })
    const mod = await import('../../../../features/ai/services/aiService')
    const result = await mod.reemplazarLogo({ logo_b64: 'logo' })
    expect(api.post).toHaveBeenCalledWith('/ai/reemplazar-logo', { logo_b64: 'logo' })
    expect(result).toEqual({ content_b64: 'new' })
  })

  it('chatConPropuesta should post to /ai/chat-propuesta', async () => {
    api.post.mockResolvedValue({ data: { reply: 'respuesta' } })
    const mod = await import('../../../../features/ai/services/aiService')
    const result = await mod.chatConPropuesta({ messages: [], content_b64: 'x' })
    expect(api.post).toHaveBeenCalledWith('/ai/chat-propuesta', { messages: [], content_b64: 'x' })
    expect(result).toEqual({ reply: 'respuesta' })
  })
})