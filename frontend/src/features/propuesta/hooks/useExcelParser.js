import { useState } from 'react'
import * as XLSX from 'xlsx'

export function useExcelParser() {
  const [excelData, setExcelData] = useState(null)
  const [error, setError] = useState(null)

  function parseFile(file) {
    setError(null)
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        // cellStyles:true intenta extraer colores de celda (soporte parcial en SheetJS libre)
        const wb = XLSX.read(e.target.result, { type: 'array', cellStyles: true })
        const resumen    = parseResumen(wb)
        const estimacion = parseEstimacion(wb)
        const alcances   = parseAlcances(wb, resumen.torres)
        const anexos     = parseAnexos(wb)
        setExcelData({ ...resumen, ...estimacion, alcances, perfiles: anexos })
      } catch (err) {
        setError(err.message)
      }
    }
    reader.readAsArrayBuffer(file)
  }

  return { excelData, error, parseFile }
}

function parseResumen(wb) {
  const ws = wb.Sheets['RESUMEN']
  if (!ws) throw new Error('Hoja RESUMEN no encontrada')
  const rows = XLSX.utils.sheet_to_json(ws, { header: 1 })
  const proyecto = rows.find(r => r[0] === 'Proyecto')?.[1] || ''
  const cliente  = rows.find(r => r[0] === 'Cliente')?.[1]  || ''
  const torres   = rows
    .filter(r => r[0] && typeof r[0] === 'string' && r[0].startsWith('Torre'))
    .map(r => ({ nombre: String(r[0]).replace('Torre', '').trim(), horas: Math.round(Number(r[1]) || 0) }))
  return { proyecto, cliente, torres }
}

function parseEstimacion(wb) {
  const ws = wb.Sheets['Estimación'] || wb.Sheets['Estimacion']
  if (!ws) return { consideraciones: [], fda: [], entregables: [] }
  const rows = XLSX.utils.sheet_to_json(ws, { header: 1 })
  const consideraciones = rows.flatMap(r => r[9] ? String(r[9]).split('.').map(s => s.trim()).filter(Boolean) : [])
  const fda             = rows.flatMap(r => r[10] ? String(r[10]).split('.').map(s => s.trim()).filter(Boolean) : [])
  const entregables     = rows
    .filter(r => r[12])
    .reduce((acc, r) => {
      const torre = String(r[0] || '').trim()
      if (!torre) return acc
      const subItems = String(r[12]).split(/\r?\n/).map(s => s.trim()).filter(Boolean)
      if (!subItems.length) return acc
      const group = acc.find(g => g.torre === torre)
      if (group) group.items.push(...subItems)
      else acc.push({ torre, items: subItems })
      return acc
    }, [])
  return { consideraciones, fda, entregables }
}

// ── Detección de color verde en celda ─────────────────────────────────────────
// SheetJS libre devuelve colores en cell.s.fgColor / cell.s.bgColor (argb o rgb)
function _rgbEsVerde(hex) {
  if (!hex || hex.length < 6) return false
  // Quitar alpha channel si viene en formato AARRGGBB (8 chars)
  const rgb = hex.length === 8 ? hex.slice(2) : hex
  const r = parseInt(rgb.slice(0, 2), 16)
  const g = parseInt(rgb.slice(2, 4), 16)
  const b = parseInt(rgb.slice(4, 6), 16)
  // Verde: canal G dominante (umbral holgado para capturar diferentes tonos)
  return g > r + 20 && g > b + 20 && g > 80
}

function _celdaEsVerde(cell) {
  if (!cell || !cell.s) return false
  const fg = cell.s.fgColor
  const bg = cell.s.bgColor
  const colorFg = fg?.argb || fg?.rgb || ''
  const colorBg = bg?.argb || bg?.rgb || ''
  return _rgbEsVerde(colorFg) || _rgbEsVerde(colorBg)
}

// ── Parseo de alcances desde hoja Estimación ─────────────────────────────────
// Estrategia de detección de fila separadora de torre:
//   1. Celda A tiene color verde (detectado via cellStyles).
//   2. Fallback: texto de col A coincide con un nombre de torre conocido
//      Y la col B está vacía (las filas de contenido siempre tienen descripción en B).
function parseAlcances(wb, torres = []) {
  const ws = wb.Sheets['Estimación'] || wb.Sheets['Estimacion']
  if (!ws) return []

  const rangeStr = ws['!ref']
  if (!rangeStr) return []
  const range = XLSX.utils.decode_range(rangeStr)

  // Set de nombres de torres normalizados para el fallback
  const torresNorm = new Set(
    (torres || []).map(t => (t.nombre || t).trim().toLowerCase())
  )

  const alcances      = []
  let   torreActual   = null
  let   itemsActuales = []

  for (let r = range.s.r; r <= range.e.r; r++) {
    const refA = XLSX.utils.encode_cell({ r, c: 0 })
    const refB = XLSX.utils.encode_cell({ r, c: 1 })
    const cellA = ws[refA]
    const cellB = ws[refB]

    const textoA = cellA ? String(cellA.v ?? '').trim() : ''
    const textoB = cellB ? String(cellB.v ?? '').trim() : ''

    if (!textoA) continue

    // ── Determinar si es fila separadora de torre ────────────────────────
    const verdeDetectado = _celdaEsVerde(cellA)
    const esFallbackTorre =
      torresNorm.has(textoA.toLowerCase()) && !textoB

    const esCabeceraTorre = verdeDetectado || esFallbackTorre

    if (esCabeceraTorre) {
      // Guardar la torre anterior antes de empezar la nueva
      if (torreActual && itemsActuales.length > 0) {
        alcances.push({ torre: torreActual, items: itemsActuales })
      }
      torreActual   = textoA
      itemsActuales = []
    } else if (torreActual) {
      // Fila de contenido: col A = título del proceso, col B = descripción
      itemsActuales.push({ titulo: textoA, descripcion: textoB })
    }
  }

  // Guardar la última torre
  if (torreActual && itemsActuales.length > 0) {
    alcances.push({ torre: torreActual, items: itemsActuales })
  }

  return alcances
}

function parseAnexos(wb) {
  const ws = wb.Sheets['Anexos']
  if (!ws) return []
  return XLSX.utils.sheet_to_json(ws, { header: 1 })
    .slice(1)
    .filter(r => r[0])
    .map(r => ({ perfil: String(r[0]).trim(), torre: String(r[1] || '').trim() }))
}
