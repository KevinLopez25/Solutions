import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    let msg = 'Error desconocido'
    
    if (err.response?.data) {
      const data = err.response.data
      
      // Si detail es un array (errores de validación Pydantic)
      if (Array.isArray(data.detail)) {
        msg = data.detail
          .map(e => `${e.loc?.[e.loc.length - 1] || 'Campo'}: ${e.msg}`)
          .join('. ')
      }
      // Si detail es un string
      else if (typeof data.detail === 'string') {
        msg = data.detail
      }
      // Si es un objeto con mensaje
      else if (typeof data.detail === 'object') {
        msg = JSON.stringify(data.detail)
      }
    }
    
    if (!msg || msg === '[object Object]') {
      msg = err.message || 'Error desconocido'
    }
    
    return Promise.reject(new Error(msg))
  }
)

export default api
