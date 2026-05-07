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
        .filter(t => t.horas > 0)
        .map(t => ({
          torre:     t.nombre,
          actividad: t.nombre,
          horas:     t.horas,
          personas:  t.personas || 1,
        }))

      const roles = (excelData?.perfiles || [])
        .filter(p => p.perfil && p.perfil.trim() !== '')

      const payload = {
        filial,
        excel_data:           excelData || {},
        torres_seleccionadas: torresSeleccionadas,
        opciones,
        perfiles_manuales:    efectivosManuales !== undefined ? efectivosManuales : perfilesManuales,
        incluir_qa:           incluirQa,
        actividades,
        roles,
      }

      const result = await generarPropuesta(payload)
      download(
        result.content_b64,
        result.filename,
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      )
    } catch (err) {
      setError(err.message)
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
