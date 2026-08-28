import api from '../../../core/api'

export async function generarCronograma(payload) {
  const { data } = await api.post('/cronograma/generar', payload)
  return data
}

export async function clasificarProductividad(perfiles) {
  const { data } = await api.post('/ai/clasificar-productividad', { perfiles })
  return data.perfiles
}
