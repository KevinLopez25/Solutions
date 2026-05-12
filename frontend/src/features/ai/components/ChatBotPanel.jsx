import { useEffect, useMemo, useRef, useState } from 'react'
import { enviarMensajeIA, modificarPropuesta, reemplazarLogo } from '../services/aiService'

const INITIAL_ASSISTANT = {
  role: 'assistant',
  content:
    '👋 Hola, soy tu asistente de IA. Puedo revisar y corregir nombres de roles en tu propuesta, o reemplazar el logo de la primera diapositiva. Usa los botones de abajo para modificar el documento generado.',
}

const DEFAULT_INSTRUCTION =
  'Corrige los nombres de roles que sean ilógicos o incompletos. ' +
  'Si el nombre es solo una tecnología o lenguaje, complétalo con su rol apropiado: ' +
  '"Java" o "Java EE" → "Desarrollador Full Stack Java", ' +
  '"React" o "ReactJS" → "Desarrollador Full Stack React", ' +
  '"Angular" → "Desarrollador Full Stack Angular", ' +
  '"Node" o "NodeJS" → "Desarrollador Backend Node.js", ' +
  '"Python" → "Desarrollador Python", ' +
  '"Golang" o "Go" → "Desarrollador Backend Go". ' +
  'Si dice "desarrollador analista de requerimientos" → "Analista de Requerimientos", ' +
  '"desarrollador arquitecto" → "Arquitecto de Soluciones", ' +
  '"desarrollador scrum master" → "Scrum Master". ' +
  'No agregues ni elimines perfiles, trabaja solo con los que ya existen en el documento.'

const IMAGE_EXTS = new Set(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'])

function isImageFile(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  return IMAGE_EXTS.has(ext)
}

export default function ChatBotPanel({ open, onToggle, proposalDraft, onProposalModified }) {
  const [messages, setMessages]       = useState([INITIAL_ASSISTANT])
  const [input, setInput]             = useState('')
  const [instruction, setInstruction] = useState(DEFAULT_INSTRUCTION)
  const [loading, setLoading]         = useState(false)
  const [attachedFile, setAttachedFile] = useState(null) // { name, content, isImage, b64 }
  const [fileLoading, setFileLoading] = useState(false)
  const [error, setError]             = useState('')
  const bodyRef   = useRef(null)
  const fileInput = useRef(null)

  const chatMessages = useMemo(
    () => messages.filter((m) => m.role !== 'system'),
    [messages],
  )

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight
  }, [chatMessages, open])

  // ── Chat normal ──────────────────────────────────────────────────────────────
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

  // ── Adjuntar archivo o imagen ────────────────────────────────────────────────
  function handleFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setFileLoading(true)
    setError('')

    if (isImageFile(file.name)) {
      const reader = new FileReader()
      reader.onload = () => {
        const b64 = reader.result.split(',')[1] // solo datos base64 sin prefijo
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

  // ── Modificar propuesta con IA ───────────────────────────────────────────────
  async function handleModifyProposal() {
    if (!proposalDraft || loading) return
    const finalInstruction = instruction.trim() || DEFAULT_INSTRUCTION
    const reviewMessage = { role: 'user', content: `Instrucción: ${finalInstruction}` }
    setMessages((prev) => [...prev, reviewMessage])
    setLoading(true)
    setError('')
    try {
      const { reply, content_b64 } = await modificarPropuesta({
        messages:    chatMessages,
        content_b64: proposalDraft.content_b64,
        instruction: finalInstruction,
      })
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
      if (onProposalModified) onProposalModified({ ...proposalDraft, content_b64 })
    } catch (err) {
      const msg = err?.message || 'Error al modificar la propuesta.'
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
            <span>Revisa tu propuesta y ajusta perfiles</span>
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

              {/* Previsualización de imagen adjunta */}
              {attachedFile?.isImage && (
                <img
                  src={`data:${attachedFile.mimeType};base64,${attachedFile.b64}`}
                  alt="preview"
                  style={{ maxWidth: '100%', maxHeight: 120, borderRadius: 8, marginTop: 6, objectFit: 'contain' }}
                />
              )}

              {/* Botón enviar archivo de texto */}
              {attachedFile && !attachedFile.isImage && (
                <button type="button" className="chatbot-send-file" onClick={handleSendFile} disabled={loading}>
                  {loading ? 'Enviando…' : 'Enviar archivo a IA'}
                </button>
              )}

              {/* Botón reemplazar logo (solo cuando hay imagen + propuesta) */}
              {attachedFile?.isImage && proposalDraft && (
                <button type="button" className="chatbot-send-file" onClick={handleReplaceLogo} disabled={loading}>
                  {loading ? 'Reemplazando…' : '🖼️ Reemplazar logo en la propuesta'}
                </button>
              )}

              {/* Sección: modificar propuesta con instrucción editable */}
              {proposalDraft && (
                <div className="chatbot-proposal-review">
                  <div><strong>Modificar propuesta:</strong> {proposalDraft.filename}</div>
                  <textarea
                    className="chatbot-input"
                    rows={3}
                    value={instruction}
                    onChange={(e) => setInstruction(e.target.value)}
                    placeholder="Escribe la instrucción para la IA…"
                    disabled={loading}
                    style={{ marginTop: 6 }}
                  />
                  <button type="button" className="chatbot-send-file" onClick={handleModifyProposal} disabled={loading}>
                    {loading ? 'Modificando…' : '✏️ Modificar documento con IA'}
                  </button>
                </div>
              )}
            </div>

            {/* ── Mensajes del chat ── */}
            <div className="chatbot-body" ref={bodyRef}>
              {chatMessages.map((message, index) => (
                <div key={`${message.role}-${index}`} className={`chatbot-message chatbot-message-${message.role}`}>
                  <span>{message.content}</span>
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
                placeholder="Escribe tu pregunta o instrucción…"
                disabled={loading}
              />
              <button className="chatbot-send" type="submit" disabled={loading || !input.trim()} aria-label="Enviar">
                {loading ? '⏳ Enviando…' : 'Enviar mensaje'}
              </button>
            </form>

            {error && <div className="chatbot-error">⚠️ {error}</div>}
            <div className="chatbot-hint">
              💡 Tip: escribe una instrucción personalizada y presiona "Modificar documento con IA", o adjunta tu logo y usa "Reemplazar logo".
            </div>
          </>
        )}
      </div>
    </div>
  )
}
