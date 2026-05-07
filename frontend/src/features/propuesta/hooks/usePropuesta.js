import { useState } from 'react'
import { generarPropuesta } from '../services/propuestaService'
import { useDownload } from '../../../shared/hooks/useDownload'

const INITIAL_PILLS = {
  perfiles:        false,
  fda:             false,
  entregables:     false,
  consideraciones: false,
}

export function usePropuesta() {
  const [filial, setFilial]              = useState('corp')
  const [excelData, setExcelData]        = useState(null)
  const [torresSeleccionadas, setTorres] = useState([])
  const [perfilesManuales, setPerfiles]  = useState([])
  const [opciones, setOpciones]          = useState(INITIAL_PILLS)
  const [incluirQa, setIncluirQa]        = useState(false)
  const [loading, setLoading]            = useState(false)
  const [error, setError]                = useState(null)
  const { download } = useDownload()

  function togglePill(key) {
    setOpciones(prev => ({ ...prev, [key]: !prev[key] }))
  }

  async function generate(efectivosManuales) {
    setLoading(true)
    setError(null)
    try {
      const actividades = (excelData?.torres || [])
        .filter(t => t && typeof t === 'object' && Number(t.horas) > 0)
        .map(t => ({
          torre:     String(t.nombre || '').trim(),
          actividad: String(t.nombre || '').trim(),
          horas:     Math.round(Number(t.horas) || 0),
          personas:  Math.max(1, Math.round(Number(t.personas) || 1)),
        }))

      const roles = (excelData?.perfiles || [])
        .filter(p => p && typeof p === 'object' && p.perfil && String(p.perfil).trim() !== '')
        .map(p => ({
          torre:     String(p.torre || '').trim(),
          perfil:    String(p.perfil || '').trim(),
          seniority: String(p.seniority || '').trim(),
          personas:  Math.max(1, Math.round(Number(p.personas) || 1)),
        }))

      // Construir un objeto limpio solo con datos necesarios
      const cleanExcelData = {
        cliente:         String(excelData?.cliente || '').trim(),
        proyecto:        String(excelData?.proyecto || '').trim(),
        torres:          (excelData?.torres || []).map(t => ({
          nombre:        String(t.nombre || '').trim(),
          horas:         Math.round(Number(t.horas) || 0),
          personas:      Math.max(1, Math.round(Number(t.personas) || 1)),
        })),
        consideraciones: (excelData?.consideraciones || []).map(c => String(c).trim()).filter(c => c.length > 0).slice(0, 20),
        fda:             (excelData?.fda || []).map(f => String(f).trim()).filter(f => f.length > 0).slice(0, 20),
        entregables:     (excelData?.entregables || []).map(e => ({
          torre: String(e.torre || '').trim(),
          items: (e.items || []).map(i => String(i).trim()).filter(i => i.length > 0).slice(0, 10)
        })).slice(0, 10),
        filename:        String(excelData?.filename || '').trim(),
      }

      const payload = {
        filial,
        excel_data:           cleanExcelData,
        torres_seleccionadas: torresSeleccionadas.filter(t => String(t).trim().length > 0),
        opciones,
        perfiles_manuales:    (efectivosManuales !== undefined ? efectivosManuales : perfilesManuales)
          .filter(p => p && typeof p === 'object' && p.rol)
          .map(p => ({
            rol:  String(p.rol || '').trim(),
            desc: String(p.desc || '').trim(),
          }))
          .slice(0, 50),
        incluir_qa:           Boolean(incluirQa),
        actividades:          actividades.slice(0, 100),
        roles:                roles.slice(0, 100),
      }

      // Validar que el payload sea serializable
      const testJSON = JSON.stringify(payload)
      if (testJSON.length > 1000000) { // 1MB max
        throw new Error('Los datos del Excel son demasiado extensos. Intenta con un archivo más pequeño.')
      }

      const result = await generarPropuesta(payload)
      download(
        result.content_b64,
        result.filename,
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      )
    } catch (err) {
      setError(err.message || 'Error al generar la propuesta')
      console.error('Generate error:', err)
    } finally {
      setLoading(false)
    }
  }

  return {
    filial, setFilial,
    excelData, setExcelData,
    torresSeleccionadas, setTorres,
    perfilesManuales, setPerfiles,
    opciones, togglePill,
    incluirQa, setIncluirQa,
    loading, error,
    generate,
  }
}
