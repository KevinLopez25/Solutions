import api from '../../../core/api'

export function enviarMensajeIA(messages) {
  return api.post('/ai/chat', { messages }).then((res) => res.data)
}

export function modificarPropuesta(payload) {
  return api.post('/ai/modificar-propuesta', payload).then((res) => res.data)
}

export function reemplazarLogo(payload) {
  return api.post('/ai/reemplazar-logo', payload).then((res) => res.data)
}

export function chatConPropuesta(payload) {
  return api.post('/ai/chat-propuesta', payload).then((res) => res.data)
}

export function completarCatalogo(payload) {
  return api.post('/ai/completar-catalogo', payload).then((res) => res.data)
}

export function completarDescripciones(payload) {
  return api.post('/ai/completar-descripciones', payload).then((res) => res.data)
}

export function sugerirDescripciones(payload) {
  return api.post('/ai/sugerir-descripciones', payload).then((res) => res.data)
}

export function aplicarDescripciones(payload) {
  return api.post('/ai/aplicar-descripciones', payload).then((res) => res.data)
}
