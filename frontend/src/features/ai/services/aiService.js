import api from '../../../core/api'

export function enviarMensajeIA(messages) {
  return api.post('/ai/chat', { messages }).then((res) => res.data)
}

export function modificarPropuesta(payload) {
  return api.post('/ai/modificar-propuesta', payload).then((res) => res.data)
}
