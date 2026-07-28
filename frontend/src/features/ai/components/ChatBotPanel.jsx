import { useEffect, useMemo, useRef, useState } from 'react'
import { chatConPropuesta, completarDescripciones, enviarMensajeIA, reemplazarLogo, sugerirDescripciones, aplicarDescripciones } from '../services/aiService'
import { useDownload } from '../../../shared/hooks/useDownload'

const INITIAL_ASSISTANT = {
  role: 'assistant',
  content:
    'Hola, soy tu asistente de IA para propuestas comerciales.\n\n' +
    'Cuando tengas una propuesta generada puedes pedirme cosas como:\n' +
    '• "Revisa y corrige los perfiles"\n' +
    '• "El perfil de Java está incompleto, corrígelo"\n' +
    '• "Completa las descripciones de los perfiles"\n' +
    '• "¿Qué perfiles hay en la propuesta?"\n\n' +
    'También puedo reemplazar el logo usando el botón de arriba.',
}

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'])

function isImageFile(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  return IMAGE_EXTS.has(ext)
}

// Placeholder que se usa en la BD cuando no hay descripción
const PLACEHOLDER_TEXT = 'Solicita al asistente IA que complete esta descripción'

export default function ChatBotPanel({ open, onToggle, proposalDraft, onProposalModified }) {
  const [messages, setMessages]         = useState([INITIAL_ASSISTANT])
  const [input, setInput]               = useState('')
  const [loading, setLoading]           = useState(false)
  const [attachedFile, setAttachedFile] = useState(null)
  const [fileLoading, setFileLoading]   = useState(false)
  const [error, setError]               = useState('')
  const [pendingDescriptions, setPendingDescriptions] = useState(true)
  const bodyRef   = useRef(null)
  const fileInput = useRef(null)
  const { download } = useDownload()

  const chatMessages = useMemo(
    () => messages.filter((m) => m.role !== 'system'),
    [messages],
  )

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [chatMessages, open])

  // Reiniciar el estado de pendientes cada vez que se carga una propuesta nueva
  useEffect(() => {
    setPendingDescriptions(true)
  }, [proposalDraft])

  // ── Estado de descripciones pendientes (el backend decide al completar) ──────
  // Se muestra el boton de completar mientras haya propuesta cargada y no se
  // haya confirmado que ya no hay descripciones pendientes.
  const profilesWithoutDescription = useMemo(
    () => (proposalDraft && pendingDescriptions ? 1 : 0),
    [proposalDraft, pendingDescriptions],
  )

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

  // ── Reemplazar logo con la imagen adjunta ────────────────────────────────────
  async function handleReplaceLogo() {
    if (!attachedFile?.isImage || !proposalDraft || loading) return
    setLoading(true)
    setError('')
    const infoMsg = { role: 'user', content: `Reemplazando el logo de la primera diapositiva con: ${attachedFile.name}` }
    setMessages((prev) => [...prev, infoMsg])
    try {
      const { content_b64 } = await reemplazarLogo({
        content_b64: proposalDraft.content_b64,
        logo_b64:    attachedFile.b64,
        logo_mime:   attachedFile.mimeType || 'image/png',
      })
      const updated = { ...proposalDraft, content_b64 }
      if (onProposalModified) onProposalModified(updated)
      setMessages((prev) => [...prev, { role: 'assistant', content: '✅ Logo reemplazado correctamente en la primera diapositiva. Descarga la propuesta para verlo.' }])
      setAttachedFile(null)
    } catch (err) {
      const msg = err?.message || 'Error al reemplazar el logo.'
      setError(msg)
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  // ── NUEVO FLUJO INTERACTIVO: Sugerir descripciones (solo muestra, no guarda) ──
  const [pendingSuggestions, setPendingSuggestions] = useState(null) // { descripciones: [...], content_b64_original: '...' }

  async function handleSugerirDescripciones() {
    if (!proposalDraft || !proposalDraft.content_b64 || loading) return

    setLoading(true)
    setError('')
    setPendingSuggestions(null)

    const infoMsg = {
      role: 'user',
      content: '🤖 Sugiere descripciones para los perfiles pendientes',
    }
    setMessages((prev) => [...prev, infoMsg])

    try {
      const { sugerencias, reply } = await sugerirDescripciones({
        content_b64: proposalDraft.content_b64,
      })

      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])

      if (sugerencias && sugerencias.length > 0) {
        setPendingSuggestions({
          descripciones: sugerencias,
          content_b64_original: proposalDraft.content_b64,
        })
      } else {
        setPendingDescriptions(false)
      }
    } catch (err) {
      const msg = err?.message || 'Error al generar sugerencias.'
      setError(msg)
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  // ── Aprobar descripciones sugeridas y aplicarlas ──
  async function handleAprobarDescripciones() {
    if (!pendingSuggestions || loading) return

    setLoading(true)
    setError('')

    const userMsg = { role: 'user', content: '✅ Aprobar descripciones sugeridas' }
    setMessages((prev) => [...prev, userMsg])

    try {
      const { reply, content_b64, modified } = await aplicarDescripciones({
        content_b64: pendingSuggestions.content_b64_original,
        descripciones: pendingSuggestions.descripciones,
      })

      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])

      if (modified && content_b64) {
        const updated = { ...proposalDraft, content_b64 }
        if (onProposalModified) onProposalModified(updated)
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: '✅ Descargando la versión con descripciones…' },
        ])
        download(
          content_b64,
          proposalDraft.filename || 'Propuesta_Actualizada.pptx',
          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )
        setPendingDescriptions(false)
      }
      setPendingSuggestions(null)
    } catch (err) {
      const msg = err?.message || 'Error al aplicar descripciones.'
      setError(msg)
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${msg}` }])
    } finally {
      setLoading(false)
    }
  }

  // ── Rechazar / cancelar sugerencias ──
  function handleCancelarSugerencias() {
    setPendingSuggestions(null)
    setMessages((prev) => [...prev, {
      role: 'assistant',
      content: '❌ Sugerencias canceladas. Puedes pedirme que genere nuevas descripciones cuando quieras.',
    }])
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
            {/* ── Botón para sugerir descripciones cuando hay perfiles sin descripción ── */}
            {proposalDraft && profilesWithoutDescription > 0 && !pendingSuggestions && (
              <div className="chatbot-complete-panel" style={{
                padding: '8px 12px',
                background: 'linear-gradient(135deg, #1a3a2a 0%, #0d2818 100%)',
                borderBottom: '1px solid #2ecc7133',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                flexWrap: 'wrap',
              }}>
                <span style={{ color: '#ffd700', fontSize: 13 }}>
                  ⚠️ {profilesWithoutDescription} perfil(es) sin descripción
                </span>
                <button
                  type="button"
                  className="chatbot-complete-btn"
                  onClick={handleSugerirDescripciones}
                  disabled={loading}
                  style={{
                    background: 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 6,
                    padding: '6px 14px',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                    whiteSpace: 'nowrap',
                  }}
                >
                  {loading ? '⏳ Generando…' : '🤖 Sugerir descripciones con IA'}
                </button>
              </div>
            )}

            {/* ── Botones de aprobar/rechazar cuando hay sugerencias pendientes ── */}
            {pendingSuggestions && (
              <div className="chatbot-complete-panel" style={{
                padding: '8px 12px',
                background: 'linear-gradient(135deg, #1a4a2a 0%, #0d3818 100%)',
                borderBottom: '1px solid #f39c1233',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                flexWrap: 'wrap',
                justifyContent: 'center',
              }}>
                <span style={{ color: '#2ecc71', fontSize: 13, fontWeight: 600 }}>
                  ✅ {pendingSuggestions.descripciones.length} sugerencia(s) lista(s)
                </span>
                <button
                  type="button"
                  onClick={handleAprobarDescripciones}
                  disabled={loading}
                  style={{
                    background: 'linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)',
                    color: '#fff',
                    border: 'none',
                    borderRadius: 6,
                    padding: '6px 14px',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {loading ? '⏳ Aplicando…' : '✅ Aprobar y aplicar'}
                </button>
                <button
                  type="button"
                  onClick={handleCancelarSugerencias}
                  disabled={loading}
                  style={{
                    background: 'transparent',
                    color: '#e74c3c',
                    border: '1px solid #e74c3c',
                    borderRadius: 6,
                    padding: '5px 14px',
                    fontSize: 12,
                    fontWeight: 600,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  ❌ Cancelar
                </button>
              </div>
            )}

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

              {attachedFile?.isImage && proposalDraft && (
                <button type="button" className="chatbot-send-file" onClick={handleReplaceLogo} disabled={loading}>
                  {loading ? 'Reemplazando…' : '🖼️ Reemplazar logo en la propuesta'}
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