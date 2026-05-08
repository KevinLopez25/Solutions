import api from '../../../core/api'

export function enviarMensajeIA(messages) {
  return api.post('/ai/chat', { messages }).then((res) => res.data)
}
