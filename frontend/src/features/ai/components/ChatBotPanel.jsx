import { useEffect, useMemo, useRef, useState } from 'react'
import { chatConPropuesta, enviarMensajeIA } from '../services/aiService'

const INITIAL_ASSISTANT = {
  role: 'assistant',
  content:
    'Hola, soy tu asistente de IA para propuestas comerciales.\n\n' +
    'Cuando tengas una propuesta generada puedes pedirme cosas como:\n' +
    '• "Revisa y corrige los perfiles"\n' +
    '• "El perfil de Java está incompleto, corrígelo"\n' +
    '• "¿Qué perfiles hay en la propuesta?"\n' +
    '• "Corrige todos los nombres que solo digan una tecnología"',
}

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'])

function isImageFile(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  return IMAGE_EXTS.has(ext)
}

export default function ChatBotPanel({ open, onToggle, proposalDraft, onProposalModified }) {
  const [messages, setMessages]         = useState([INITIAL_ASSISTANT])
  const [input, setInput]               = useState('')
  const [loading, setLoading]           = useState(false)
  const [attachedFile, setAttachedFile] = useState(null)
  const [fileLoading, setFileLoading]   = useState(false)
  const [error, setError]               = useState('')
  const bodyRef   = useRef(null)
  const fileInput = useRef(null)

  const chatMessages = useMemo(
    () => messages.filter((m) => m.role !== 'system'),
    [messages],
  )

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [chatMessages, open])

  // ── Chat principal (con o sin propuesta) ─────────────────────────────────────
  async function handleSend(event) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return

    const userMessage = { role: 'user', content: trimmed }
    const next = [...chatMessages, userMessage]
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError('')
    try {
      if (proposalDraft) {
        const { reply, content_b64, modified } = await chatConPropuesta({
          messages:    next,
          content_b64: proposalDraft.content_b64,
        })
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
        if (modified && content_b64 && onProposalModified) {
          onProposalModified({ ...proposalDraft, content_b64 })
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: '✅ Propuesta actualizada. Descárgala para ver los cambios.' },
          ])
        }
      } else {
        const { reply } = await enviarMensajeIA(next)
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      }
    } catch (err) {
      const msg = err?.message || 'Error al conectar con IA.'
      setError(msg)
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  // ── Adjuntar archivo o imagen ────────────────────────────────────────────────
  function handleFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setFileLoading(true)
    setError('')

    if (isImageFile(file.name)) {
      const reader = new FileReader()
      reader.onload = () => {
        const b64 = reader.result.split(',')[1]
        setAttachedFile({ name: file.name, isImage: true, b64, mimeType: file.type })
        setFileLoading(false)
      }
      reader.onerror = () => { setError('No se pudo leer la imagen.'); setFileLoading(false) }
      reader.readAsDataURL(file)
    } else {
      const reader = new FileReader()
      reader.onload = () => {
        setAttachedFile({ name: file.name, isImage: false, content: String(reader.result || '').slice(0, 22000) })
        setFileLoading(false)
      }
      reader.onerror = () => { setError('No se pudo leer el archivo.'); setFileLoading(false) }
      reader.readAsText(file)
    }
    event.target.value = ''
  }

  // ── Enviar archivo de texto a la IA ─────────────────────────────────────────
  async function handleSendFile() {
    if (!attachedFile || attachedFile.isImage || loading) return
    const fileMessage = {
      role: 'user',
      content: `Adjunto archivo: ${attachedFile.name}. Revisa su contenido y corrige la propuesta, especialmente los roles de perfil y la escritura.\n\n${attachedFile.content}`,
    }
    const next = [...chatMessages, fileMessage]
    setMessages((prev) => [...prev, fileMessage])
    setAttachedFile(null)
    setLoading(true)
    setError('')
    try {
      const { reply } = await enviarMensajeIA(next)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
    } catch (err) {
      const msg = err?.message || 'Error al conectar con IA.'
      setError(msg)
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={`chatbot-root ${open ? 'is-open' : 'is-closed'}`}>
      <div className="chatbot-card chatbot-card-modern">
        <div className="chatbot-header">
          <div>
            <strong>Asistente IA</strong>
            <span>{proposalDraft ? `Propuesta cargada: ${proposalDraft.filename}` : 'Revisa tu propuesta y ajusta perfiles'}</span>
          </div>
          <button type="button" className="chatbot-toggle" onClick={onToggle} aria-label={open ? 'Cerrar chat' : 'Abrir chat'}>
            {open ? '✕' : '💬'}
          </button>
        </div>

        {open && (
          <>
            {/* ── Sección: adjuntar archivos / imágenes ── */}
            <div className="chatbot-file-panel">
              <label className="chatbot-file-label" htmlFor="chat-file-upload">
                <span>Adjuntar archivo o imagen</span>
                <small>txt, md, json, csv, png, jpg, gif…</small>
              </label>
              <input
                id="chat-file-upload"
                ref={fileInput}
                className="chatbot-file-input"
                type="file"
                accept=".txt,.md,.json,.csv,.png,.jpg,.jpeg,.gif,.webp,.svg"
                onChange={handleFileChange}
                disabled={fileLoading || loading}
              />

              {attachedFile && (
                <div className="chatbot-file-chip">
                  <span>{attachedFile.isImage ? '🖼️' : '📄'} {attachedFile.name}</span>
                  <button type="button" onClick={() => setAttachedFile(null)}>✕</button>
                </div>
              )}

              {attachedFile?.isImage && (
                <img
                  src={`data:${attachedFile.mimeType};base64,${attachedFile.b64}`}
                  alt="preview"
                  style={{ maxWidth: '100%', maxHeight: 120, borderRadius: 8, marginTop: 6, objectFit: 'contain' }}
                />
              )}

              {attachedFile && !attachedFile.isImage && (
                <button type="button" className="chatbot-send-file" onClick={handleSendFile} disabled={loading}>
                  {loading ? 'Enviando…' : 'Enviar archivo a IA'}
                </button>
              )}
            </div>

            {/* ── Mensajes del chat ── */}
            <div className="chatbot-body" ref={bodyRef}>
              {chatMessages.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`chatbot-message chatbot-message-${message.role}`}>
                  <span style={{ whiteSpace: 'pre-line' }}>{message.content}</span>
                </div>
              ))}
              {loading && (
                <div className="chatbot-message chatbot-message-assistant">
                  <span className="chatbot-typing">✓ Procesando…</span>
                </div>
              )}
            </div>

            {/* ── Input de chat ── */}
            <form className="chatbot-form" onSubmit={handleSend}>
              <textarea
                className="chatbot-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(e) } }}
                rows={3}
                placeholder={
                  proposalDraft
                    ? 'Ej: "Revisa y corrige los perfiles", "Corrige el perfil de Java"…'
                    : 'Escribe tu pregunta o instrucción…'
                }
                disabled={loading}
              />
              <button className="chatbot-send" type="submit" disabled={loading || !input.trim()} aria-label="Enviar">
                {loading ? '⏳ Enviando…' : 'Enviar mensaje'}
              </button>
            </form>

            {error && <div className="chatbot-error">⚠️ {error}</div>}
            {proposalDraft && (
              <div className="chatbot-hint">
                💡 Escríbeme en lenguaje natural. Ej: "Corrige todos los perfiles que solo digan una tecnología" o "El perfil .NET está mal, arréglalo".
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
