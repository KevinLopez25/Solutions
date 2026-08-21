import { useState } from 'react'
import { generarPropuesta } from '../services/propuestaService'
import { useDownload } from '../../../shared/hooks/useDownload'

const INITIAL_PILLS = {
  perfiles:        false,
  fda:             false,
  entregables:     false,
  consideraciones: false,
}

function buildProposalSummary(payload) {
  const lines = []
  const excel = payload.excel_data || {}

  lines.push(`Filial: ${payload.filial || 'N/A'}`)
  lines.push(`Cliente: ${excel.cliente || 'N/D'}`)
  lines.push(`Proyecto: ${excel.proyecto || 'N/D'}`)
  lines.push(`Archivo origen: ${excel.filename || 'Ninguno'}`)
  lines.push(`QA: ${payload.incluir_qa ? 'Sí' : 'No'}`)
  lines.push(`Horas laborables por semana: ${payload.horas_semanales || 42}`)
  lines.push(`Secciones con genéricos: ${Object.entries(payload.opciones)
    .filter(([, enabled]) => enabled)
    .map(([key]) => key)
    .join(', ') || 'Ninguna'}`)
  lines.push(`Torres seleccionadas: ${payload.torres_seleccionadas.length ? payload.torres_seleccionadas.join(', ') : 'Ninguna'}`)

  if (excel.torres?.length) {
    lines.push(`Torres detectadas (${excel.torres.length}):`)
    excel.torres.slice(0, 8).forEach((t, idx) => {
      lines.push(` ${idx + 1}. ${t.nombre} — ${t.horas} hrs, ${t.personas} personas`)
    })
  }

  const mappedRoles = (payload.roles || []).slice(0, 10)
  if (mappedRoles.length) {
    lines.push(`Roles detectados (${payload.roles.length}):`)
    mappedRoles.forEach((r, idx) => {
      lines.push(` ${idx + 1}. ${r.perfil || r.rol || 'sin nombre'} — ${r.torre || 'general'} (${r.personas || '1'})`)
    })
  }

  const manualRoles = (payload.perfiles_manuales || []).slice(0, 10)
  if (manualRoles.length) {
    lines.push(`Perfiles manuales (${payload.perfiles_manuales.length}):`)
    manualRoles.forEach((r, idx) => {
      lines.push(` ${idx + 1}. ${r.rol} — ${r.desc || 'sin descripción'}`)
    })
  }

  if (excel.consideraciones?.length) {
    lines.push(`Consideraciones (${excel.consideraciones.length}): ${excel.consideraciones.slice(0, 5).join('; ')}`)
  }
  if (excel.fda?.length) {
    lines.push(`FDA (${excel.fda.length}): ${excel.fda.slice(0, 5).join('; ')}`)
  }
  if (excel.entregables?.length) {
    lines.push(`Entregables (${excel.entregables.length}):`)
    excel.entregables.slice(0, 5).forEach((entry, idx) => {
      if (entry.items?.length) {
        lines.push(` ${idx + 1}. ${entry.torre}: ${entry.items.slice(0, 4).join(', ')}`)
      }
    })
  }

  return lines.join('\n')
}

export function usePropuesta() {
  const [filial, setFilial]              = useState('corp')
  const [excelData, setExcelData]        = useState(null)
  const [torresSeleccionadas, setTorres] = useState([])
  const [perfilesManuales, setPerfiles]  = useState([])
  const [opciones, setOpciones]          = useState(INITIAL_PILLS)
  const [incluirQa, setIncluirQa]          = useState(false)
  const [asIsEnabled, setAsIsEnabled]      = useState(false)
  const [asIsDescription, setAsIsDescription] = useState('')
  const [horasSemanales, setHorasSemanales] = useState(42)
  const [loading, setLoading]              = useState(false)
  const [error, setError]                  = useState(null)
  const [proposalDraft, setProposalDraft]  = useState(null)
  const { download } = useDownload()
  var [iaAlcance, setIaAlcance] = useState(false)

  // Template personalizado (subido por el usuario)
  const [templateName, setTemplateName] = useState(null)
  const [templateSection, setTemplateSection] = useState('default')
  const [applyingTemplate, setApplyingTemplate] = useState(false)

  function togglePill(key) {
    setOpciones(prev => ({ ...prev, [key]: !prev[key] }))
  }

  async function generate(efectivosManuales, useTemplate = false) {
    setLoading(true)
    setError(null)
    setProposalDraft(null)
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
        perfiles:        (excelData?.perfiles || [])
          .filter(p => p && typeof p === 'object' && p.perfil && String(p.perfil).trim() !== '')
          .map(p => ({
            torre:     String(p.torre || '').trim(),
            perfil:    String(p.perfil || '').trim(),
            seniority: String(p.seniority || '').trim(),
            personas:  Math.max(1, Math.round(Number(p.personas) || 1)),
            horas:     Math.round(Number(p.horas) || 0),
          })),
        consideraciones: (excelData?.consideraciones || []).map(c => String(c).trim()).filter(c => c.length > 0).slice(0, 20),
        fda:             (excelData?.fda || []).map(f => String(f).trim()).filter(f => f.length > 0).slice(0, 20),
        entregables:     (excelData?.entregables || []).map(e => ({
          torre: String(e.torre || '').trim(),
          items: (e.items || []).map(i => String(i).trim()).filter(i => i.length > 0).slice(0, 10)
        })).slice(0, 10),
        alcances:        (excelData?.alcances || []).map(a => ({
          torre: String(a.torre || '').trim(),
          items: (a.items || []).map(i => ({
            titulo:      String(i.titulo || '').trim(),
            descripcion: String(i.descripcion || '').trim(),
          })).filter(i => i.titulo.length > 0).slice(0, 30),
        })).filter(a => a.torre.length > 0).slice(0, 20),
        filename:        String(excelData?.filename || '').trim(),
      }

      const cleanAsIsDescription = String(asIsDescription || '').trim()
      if (asIsEnabled && !cleanAsIsDescription) {
        throw new Error('Describe el estado actual para generar AS-IS y TO-BE.')
      }

      const payload = {
        filial,
        horas_semanales: Math.max(1, Number(horasSemanales) || 42),
        excel_data:           cleanExcelData,
        torres_seleccionadas: torresSeleccionadas.filter(t => String(t).trim().length > 0),
        opciones:             { ...opciones, usar_ia_alcances: Boolean(iaAlcance) },
        perfiles_manuales:    (efectivosManuales !== undefined ? efectivosManuales : perfilesManuales)
          .filter(p => p && typeof p === 'object' && p.rol)
          .map(p => ({
            rol:  String(p.rol || '').trim(),
            desc: String(p.desc || '').trim(),
          }))
          .slice(0, 50),
        incluir_qa:           Boolean(incluirQa),
        incluir_as_is_to_be:  Boolean(asIsEnabled),
        as_is_description:    cleanAsIsDescription,
        actividades:          actividades.slice(0, 100),
        roles:                roles.slice(0, 100),
      }

      // Incluir template_name si se solicita usar plantilla personalizada
      if (useTemplate && templateName) {
        payload.template_name = templateName
        payload.template_section = templateSection
      }

      // Validar que el payload sea serializable
      const testJSON = JSON.stringify(payload)
      if (testJSON.length > 1000000) { // 1MB max
        throw new Error('Los datos del Excel son demasiado extensos. Intenta con un archivo más pequeño.')
      }

      const result = await generarPropuesta(payload)
      const draft = {
        filename: result.filename,
        content_b64: result.content_b64,
        summary: buildProposalSummary(payload),
      }
      setProposalDraft(draft)
      return draft
    } catch (err) {
      setError(err.message || 'Error al generar la propuesta')
      console.error('Generate error:', err)
      return null
    } finally {
      setLoading(false)
      setApplyingTemplate(false)
    }
  }

  async function applyTemplateToProposal(efectivosManuales) {
    if (!templateName) return
    setApplyingTemplate(true)
    setError(null)
    return generate(efectivosManuales, true)
  }

  function downloadProposal(draft) {
    if (!draft) return
    download(
      draft.content_b64,
      draft.filename,
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    )
  }

  return {
    filial, setFilial,
    excelData, setExcelData,
    torresSeleccionadas, setTorres,
    perfilesManuales, setPerfiles,
    opciones, togglePill,
    incluirQa, setIncluirQa,
    asIsEnabled, setAsIsEnabled,
    asIsDescription, setAsIsDescription,
    horasSemanales, setHorasSemanales,
    loading, error,
    proposalDraft,
    generate,
    downloadProposal,
    iaAlcance, 
    setIaAlcance,
    templateName, setTemplateName,
    templateSection, setTemplateSection,
    applyingTemplate,
    applyTemplateToProposal,
  }
}