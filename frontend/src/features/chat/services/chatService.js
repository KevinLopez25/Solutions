import api from '../../../core/api'

export async function sendMessage({ mensaje, historial, contexto_propuesta }) {
  const { data } = await api.post('/ia/chat', { mensaje, historial, contexto_propuesta })
  return data
}

export async function validarPerfiles(perfiles) {
  const { data } = await api.post('/ia/validar-perfiles', { perfiles })
  return data
}

export async function confirmarPerfil({ nombre, torre }) {
  const { data } = await api.post('/ia/confirmar-perfil', { nombre, torre })
  return data
}
