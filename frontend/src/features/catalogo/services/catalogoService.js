import api from '../../../core/api'

export const getTorres      = ()               => api.get('/catalogo/torres').then(r => r.data)
export const createTorre    = (nombre)         => api.post('/catalogo/torres', { nombre }).then(r => r.data)
export const deleteTorre    = (id)             => api.delete(`/catalogo/torres/${id}`)

export const getPerfiles    = (torreId)        => api.get('/catalogo/perfiles', { params: torreId ? { torre_id: torreId } : {} }).then(r => r.data)
export const createPerfil   = (data)           => api.post('/catalogo/perfiles', data).then(r => r.data)
export const updatePerfil   = (id, data)       => api.put(`/catalogo/perfiles/${id}`, data).then(r => r.data)
export const deletePerfil   = (id)             => api.delete(`/catalogo/perfiles/${id}`)

export const getConsideraciones = (torreId)    => api.get('/catalogo/consideraciones', { params: torreId ? { torre_id: torreId } : {} }).then(r => r.data)
export const createConsideracion= (data)       => api.post('/catalogo/consideraciones', data).then(r => r.data)
export const updateConsideracion= (id, data)   => api.put(`/catalogo/consideraciones/${id}`, data).then(r => r.data)
export const deleteConsideracion= (id)         => api.delete(`/catalogo/consideraciones/${id}`)

export const getEntregables   = (torreId)      => api.get('/catalogo/entregables', { params: torreId ? { torre_id: torreId } : {} }).then(r => r.data)
export const createEntregable = (data)         => api.post('/catalogo/entregables', data).then(r => r.data)
export const updateEntregable = (id, data)     => api.put(`/catalogo/entregables/${id}`, data).then(r => r.data)
export const deleteEntregable = (id)           => api.delete(`/catalogo/entregables/${id}`)

export const getFueraAlcance  = (torreId)      => api.get('/catalogo/fuera-del-alcance', { params: torreId ? { torre_id: torreId } : {} }).then(r => r.data)
export const createFueraAlcance=(data)         => api.post('/catalogo/fuera-del-alcance', data).then(r => r.data)
export const updateFueraAlcance=(id, data)     => api.put(`/catalogo/fuera-del-alcance/${id}`, data).then(r => r.data)
export const deleteFueraAlcance=(id)           => api.delete(`/catalogo/fuera-del-alcance/${id}`)
