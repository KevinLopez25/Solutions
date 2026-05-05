import api from '../../../core/api'

export async function generarPropuesta(payload) {
  const { data } = await api.post('/propuesta/generar', payload)
  return data
}

export async function getPerfilesCatalog(torreId) {
  const params = torreId ? { torre_id: torreId } : {}
  const { data } = await api.get('/catalogo/perfiles', { params })
  return data
}
