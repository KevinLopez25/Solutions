import api from '../../../core/api'

export async function generarCronograma(payload) {
  const { data } = await api.post('/cronograma/generar', payload)
  return data
}
