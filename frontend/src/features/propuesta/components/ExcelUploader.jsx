import { useRef, useState } from 'react'
import * as XLSX from 'xlsx'

export default function ExcelUploader({ onParsed }) {
  const inputRef = useRef(null)
  const [filename, setFilename] = useState(null)
  const [error, setError] = useState(null)

  function handleChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const wb = XLSX.read(ev.target.result, { type: 'array' })
        const data = parse(wb)
        setFilename(file.name)
        onParsed?.(data)
      } catch (err) {
        setError(err.message)
      }
    }
    reader.readAsArrayBuffer(file)
  }

  return (
    <div className="excel-uploader">
      <button type="button" onClick={() => inputRef.current?.click()} className="btn-secondary">
        Seleccionar Excel de estimación
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls"
        onChange={handleChange}
        style={{ display: 'none' }}
      />
      {filename && <p className="success-text">Cargado: {filename}</p>}
      {error && <p className="error-text">{error}</p>}
    </div>
  )
}

function parse(wb) {
  const resumen    = parseResumen(wb)
  const estimacion = parseEstimacion(wb)
  const perfiles   = parseAnexos(wb)
  return { ...resumen, ...estimacion, perfiles }
}

function parseResumen(wb) {
  const ws = wb.Sheets['RESUMEN']
  if (!ws) throw new Error('Hoja RESUMEN no encontrada')
  const rows = XLSX.utils.sheet_to_json(ws, { header: 1 })
  const proyecto = rows.find(r => r[0] === 'Proyecto')?.[1] || ''
  const cliente  = rows.find(r => r[0] === 'Cliente')?.[1]  || ''
  const torres   = rows
    .filter(r => r[0] && typeof r[0] === 'string' && r[0].startsWith('Torre'))
    .map(r => ({ nombre: String(r[0]).replace('Torre', '').trim(), horas: Number(r[1]) || 0 }))
  return { proyecto, cliente, torres }
}

function parseEstimacion(wb) {
  const ws = wb.Sheets['Estimación'] || wb.Sheets['Estimacion']
  if (!ws) return { consideraciones: [], fda: [], entregables: [] }
  const rows = XLSX.utils.sheet_to_json(ws, { header: 1 })
  const consideraciones = rows.flatMap(r => r[9]  ? String(r[9]).split('.').map(s => s.trim()).filter(Boolean) : [])
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
