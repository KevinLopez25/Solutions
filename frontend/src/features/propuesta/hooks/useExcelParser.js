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
        const wb = XLSX.read(e.target.result, { type: 'array' })
        const resumen    = parseResumen(wb)
        const estimacion = parseEstimacion(wb)
        const anexos     = parseAnexos(wb)
        setExcelData({ ...resumen, ...estimacion, perfiles: anexos })
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
      const item  = String(r[12]).trim()
      if (!torre || !item) return acc
      const group = acc.find(g => g.torre === torre)
      if (group) group.items.push(item)
      else acc.push({ torre, items: [item] })
      return acc
    }, [])
  return { consideraciones, fda, entregables }
}

function parseAnexos(wb) {
  const ws = wb.Sheets['Anexos']
  if (!ws) return []
  return XLSX.utils.sheet_to_json(ws, { header: 1 })
    .slice(1)
    .filter(r => r[0])
    .map(r => ({ perfil: String(r[0]).trim(), torre: String(r[1] || '').trim() }))
}
