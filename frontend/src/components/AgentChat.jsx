import { useState, useRef, useEffect } from 'react'
import { sendMessage } from '../features/chat/services/chatService'
import { generarPropuesta } from '../features/propuesta/services/propuestaService'
import { useDownload } from '../shared/hooks/useDownload'

const INITIAL_MESSAGE = {
  role: 'assistant',
  content: '¡Hola! Soy Peri, el asistente de Periferia IT 👋\n¿Cuál es el nombre del cliente para esta propuesta?',
}

export default function AgentChat({ isOpen, onClose }) {
  const [messages, setMessages]             = useState([INITIAL_MESSAGE])
  const [contexto, setContexto]             = useState({})
  const [input, setInput]                   = useState('')
  const [loading, setLoading]               = useState(false)
  const [quickOptions, setQuickOptions]     = useState([])
  const [readyConfig, setReadyConfig]       = useState(null)
  const [generating, setGenerating]         = useState(false)
  const [genError, setGenError]             = useState(null)
  const endRef                              = useRef(null)
  const inputRef                            = useRef(null)
  const { download }                        = useDownload()

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 120)
  }, [isOpen])

  async function send(text) {
    const content = (text || input).trim()
    if (!content || loading) return
    setInput('')
    setQuickOptions([])

    const userMsg = { role: 'user', content }
    const historial = [...messages, userMsg]
    setMessages(historial)
    setLoading(true)

    try {
      const res = await sendMessage({
        mensaje: content,
        historial: messages,
        contexto_propuesta: contexto,
      })

      const botMsg = { role: 'assistant', content: res.respuesta }
      setMessages(prev => [...prev, botMsg])
      setContexto(res.contexto_actualizado || {})
      setQuickOptions(res.quick_options || [])

      if (res.accion === 'generar_ppt' && res.config_propuesta) {
        setReadyConfig(res.config_propuesta)
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Tuve un problema conectando con el servidor. ¿Lo intentamos de nuevo?',
      }])
    } finally {
      setLoading(false)
    }
  }

  async function handleGenerate() {
    if (!readyConfig) return
    setGenerating(true)
    setGenError(null)
    try {
      const result = await generarPropuesta(readyConfig)
      download(result.content_b64, result.filename, 'application/vnd.openxmlformats-officedocument.presentationml.presentation')
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '¡Listo! Tu propuesta se está descargando. ¿Necesitas ajustar algo más?',
      }])
      setReadyConfig(null)
    } catch (err) {
      setGenError('No se pudo generar la propuesta. Verifica la configuración e intenta de nuevo.')
    } finally {
      setGenerating(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  function formatContent(text) {
    return text.split('\n').map((line, i) => (
      <span key={i}>{line}{i < text.split('\n').length - 1 && <br />}</span>
    ))
  }

  return (
    <div className={`ac-panel${isOpen ? ' ac-open' : ''}`}>
      {/* Header */}
      <div className="ac-header">
        <div className="ac-header-left">
          <div className="ac-avatar">P</div>
          <div>
            <div className="ac-name">Agente Periferia</div>
            <div className="ac-status">
              <span className="ac-dot" />
              online
            </div>
          </div>
        </div>
        <button className="ac-close" onClick={onClose} aria-label="Cerrar">✕</button>
      </div>

      {/* Messages */}
      <div className="ac-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`ac-msg ac-msg-${msg.role}`}>
            {msg.role === 'assistant' && <div className="ac-msg-avatar">P</div>}
            <div className="ac-bubble">{formatContent(msg.content)}</div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="ac-msg ac-msg-assistant">
            <div className="ac-msg-avatar">P</div>
            <div className="ac-bubble ac-typing">
              <span /><span /><span />
            </div>
          </div>
        )}

        {/* Ready to generate */}
        {readyConfig && !loading && (
          <div className="ac-generate-block">
            <div className="ac-generate-label">🚀 Propuesta lista para generar</div>
            {genError && <div className="ac-gen-error">{genError}</div>}
            <button
              className="ac-generate-btn"
              onClick={handleGenerate}
              disabled={generating}
            >
              {generating ? '⏳ Generando...' : '⬇ Descargar PPT'}
            </button>
          </div>
        )}

        <div ref={endRef} />
      </div>

      {/* Quick options */}
      {quickOptions.length > 0 && !loading && (
        <div className="ac-opts">
          {quickOptions.map((opt, i) => (
            <button key={i} className="ac-opt" onClick={() => send(opt)}>
              {opt}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="ac-input-row">
        <textarea
          ref={inputRef}
          className="ac-input"
          rows={1}
          placeholder="Escribe aquí..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
        />
        <button
          className="ac-send"
          onClick={() => send()}
          disabled={loading || !input.trim()}
          aria-label="Enviar"
        >
          ↑
        </button>
      </div>
    </div>
  )
}
