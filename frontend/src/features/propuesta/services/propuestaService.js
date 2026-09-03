import api from '../../../core/api'

export async function generarPropuesta(payload) {
  const { data } = await api.post('/propuesta/generar', payload)
  return data
}

export async function subirPlantillaTemplate({ file, filial, section, templateName }) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('filial', filial)
  formData.append('section', section)
  if (templateName) formData.append('template_name', templateName)

  const { data } = await api.post('/propuesta/plantillas/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getPerfilesCatalog(torreId) {
  const params = torreId ? { torre_id: torreId } : {}
  const { data } = await api.get('/catalogo/perfiles', { params })
  return data
}

export async function buscarTarjetasComerciales(q, pais) {
  const { data } = await api.get('/propuesta/tarjetas-comerciales', {
    params: { q: q || '', pais: pais || '' },
  })
  return data
}

export async function listarPaisesTarjetas() {
  const { data } = await api.get('/propuesta/paises-tarjetas')
  return data
}

export async function subirTarjetaComercial({ file, nombre, pais }) {
  const formData = new FormData()
  formData.append('file', file)
  if (nombre) formData.append('nombre', nombre)
  if (pais) formData.append('pais', pais)
  const { data } = await api.post('/propuesta/tarjetas-comerciales/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function eliminarTarjetaComercial(nombre, pais) {
  const { data } = await api.delete(`/propuesta/tarjetas-comerciales/${encodeURIComponent(pais || '')}/${encodeURIComponent(nombre)}`)
  return data
}
