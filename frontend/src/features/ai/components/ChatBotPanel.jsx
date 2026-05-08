import { useEffect, useMemo, useRef, useState } from 'react'
import { enviarMensajeIA } from '../services/aiService'

const INITIAL_ASSISTANT = {
  role: 'assistant',
  content:
    '👋 Hola, soy tu asistente de IA especializado en revisar propuestas. Puedo detectar errores como "desarrollador analista de requerimientos" y corregirlos a "Analista de Requerimientos". Adjunta tu propuesta para que revise perfiles y redacción.',
}

const MAX_FILE_LENGTH = 22000

export default function ChatBotPanel({ open, onToggle, proposalDraft, onReviewRequested }) {
  const [messages, setMessages] = useState([INITIAL_ASSISTANT])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [attachedFile, setAttachedFile] = useState(null)
  const [fileLoading, setFileLoading] = useState(false)
  const [error, setError] = useState('')
  const bodyRef = useRef(null)

  const chatMessages = useMemo(
    () => messages.filter((message) => message.role !== 'system'),
    [messages]
  )

  useEffect(() => {
    if (bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight
    }
  }, [chatMessages, open])

  async function handleSend(event) {
    event.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return

    const userMessage = { role: 'user', content: trimmed }
    const nextMessages = [...chatMessages, userMessage]
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError('')

    try {
      const { reply } = await enviarMensajeIA(nextMessages)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
    } catch (err) {
      const message = err?.message || 'Error al conectar con IA. Verifica tu conexión.'
      setError(message)
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${message}` }])
    } finally {
      setLoading(false)
    }
  }

  async function handleFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return

    setFileLoading(true)
    setError('')

    const reader = new FileReader()
    reader.onload = () => {
      const content = String(reader.result || '')
      setAttachedFile({ name: file.name, content: content.slice(0, MAX_FILE_LENGTH) })
      setFileLoading(false)
    }
    reader.onerror = () => {
      setError('No se pudo leer el archivo. Usa un archivo de texto plano.')
      setFileLoading(false)
    }
    reader.readAsText(file)
  }

  async function handleSendFile() {
    if (!attachedFile || loading) return

    const fileMessage = {
      role: 'user',
      content: `Adjunto archivo: ${attachedFile.name}. Revisa su contenido y corrige la propuesta, especialmente los roles de perfil y la escritura. El contenido es:\n\n${attachedFile.content}`,
    }

    const nextMessages = [...chatMessages, fileMessage]
    setMessages((prev) => [...prev, fileMessage])
    setAttachedFile(null)
    setLoading(true)
    setError('')

    try {
      const { reply } = await enviarMensajeIA(nextMessages)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
    } catch (err) {
      const message = err?.message || 'Error al conectar con IA. Verifica tu conexión.'
      setError(message)
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${message}` }])
    } finally {
      setLoading(false)
    }
  }

  async function handleReviewProposal() {
    if (!proposalDraft || loading) return

    const reviewPrompt = input.trim() ||
      'Revisa esta propuesta generada y busca errores en roles, nomenclatura, redacción y estructura.'

    const reviewMessage = {
      role: 'user',
      content: `He generado una propuesta llamada ${proposalDraft.filename}. Usa el siguiente resumen para revisarla:\n\n${proposalDraft.summary}\n\nPor favor realiza la revisión con base en esta petición:\n${reviewPrompt}`,
    }

    const nextMessages = [...chatMessages, reviewMessage]
    setMessages((prev) => [...prev, reviewMessage])
    setInput('')
    setLoading(true)
    setError('')
    if (onReviewRequested) onReviewRequested()

    try {
      const { reply } = await enviarMensajeIA(nextMessages)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
    } catch (err) {
      const message = err?.message || 'Error al conectar con IA. Verifica tu conexión.'
      setError(message)
      setMessages((prev) => [...prev, { role: 'assistant', content: `⚠️ ${message}` }])
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
          <button
            type="button"
            className="chatbot-toggle"
            onClick={onToggle}
            aria-label={open ? 'Cerrar chat' : 'Abrir chat'}
          >
            {open ? '✕' : '💬'}
          </button>
        </div>

        {open && (
          <>
            <div className="chatbot-intro">
              📎 Puedes adjuntar archivos de texto para que revise tu propuesta y corrija etiquetas de perfil.
            </div>

            <div className="chatbot-file-panel">
              <label className="chatbot-file-label" htmlFor="chat-file-upload">
                <span>Adjuntar archivo</span>
                <small>txt, md, json o csv</small>
              </label>
              <input
                id="chat-file-upload"
                className="chatbot-file-input"
                type="file"
                accept=".txt,.md,.json,.csv"
                onChange={handleFileChange}
                disabled={fileLoading || loading}
              />
              {attachedFile && (
                <div className="chatbot-file-chip">
                  <span>{attachedFile.name}</span>
                  <button type="button" onClick={() => setAttachedFile(null)}>
                    ✕
                  </button>
                </div>
              )}
              {attachedFile && (
                <button
                  type="button"
                  className="chatbot-send-file"
                  onClick={handleSendFile}
                  disabled={loading}
                >
                  {loading ? 'Enviando archivo...' : 'Enviar archivo a IA'}
                </button>
              )}
              {proposalDraft && (
                <div className="chatbot-proposal-review">
                  <div>
                    <strong>Propuesta lista para revisión:</strong> {proposalDraft.filename}
                  </div>
                  <button
                    type="button"
                    className="chatbot-send-file"
                    onClick={handleReviewProposal}
                    disabled={loading}
                  >
                    {loading ? 'Revisando propuesta...' : 'Revisar propuesta generada'}
                  </button>
                </div>
              )}
            </div>

            <div className="chatbot-body" ref={bodyRef}>
              {chatMessages.map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`chatbot-message chatbot-message-${message.role}`}
                >
                  <span>{message.content}</span>
                </div>
              ))}
              {loading && (
                <div className="chatbot-message chatbot-message-assistant">
                  <span className="chatbot-typing">✓ Escribiendo...</span>
                </div>
              )}
            </div>
            <form className="chatbot-form" onSubmit={handleSend}>
              <textarea
                className="chatbot-input"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSend(e)
                  }
                }}
                rows={3}
                placeholder="Escribe tu texto, describe tu propuesta o sube un archivo..."
                disabled={loading}
              />
              <button
                className="chatbot-send"
                type="submit"
                disabled={loading || !input.trim()}
                aria-label="Enviar mensaje"
              >
                {loading ? '⏳ Enviando...' : 'Enviar mensaje'}
              </button>
            </form>
            {error && <div className="chatbot-error">⚠️ {error}</div>}
            <div className="chatbot-hint">
              💡 Consejo: pide que revise los perfiles de tu propuesta y no anteponga "desarrollador" a roles como Analista, Arquitecto o Scrum Master.
            </div>
          </>
        )}
      </div>
    </div>
  )
}
