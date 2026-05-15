import { useRef, useState } from 'react'
import * as XLSX from 'xlsx'
import { TORRE_RESUMEN_MAP } from '../../../core/constants'

export default function ExcelUploader({ onParsed }) {
  const inputRef = useRef(null)
  const [filename, setFilename] = useState(null)
  const [error, setError] = useState(null)
  const [dragging, setDragging] = useState(false)

  function process(file) {
    if (!file) return
    setError(null)
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const wb = XLSX.read(ev.target.result, { type: 'array' })
        const data = parse(wb, file.name)
        setFilename(file.name)
        onParsed?.(data)
      } catch (err) {
        setError(err.message)
      }
    }
    reader.readAsArrayBuffer(file)
  }

  function handleChange(e) { process(e.target.files?.[0]) }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    process(e.dataTransfer.files?.[0])
  }

  function clearFile(e) {
    e.stopPropagation()
    setFilename(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <div
      className={`uzone${filename ? ' done' : ''}${dragging ? ' over' : ''}`}
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input ref={inputRef} type="file" accept=".xlsx,.xls" onChange={handleChange} />

      <div className="uinner">
        <div className="uglph">📊</div>
        <div className="uh">Arrastra el archivo aquí</div>
        <div className="up">o <b>haz clic para seleccionar</b></div>
        <div className="uchips">
          <span className="uchip">XLSX</span>
          <span className="uchip">XLS</span>
        </div>
      </div>

      {filename && (
        <div className="usuccess show">
          <span style={{ fontSize: '18px' }}>✅</span>
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {filename}
          </span>
          <span className="uchange" onClick={clearFile}>Cambiar</span>
        </div>
      )}

      {error && (
        <p className="err-txt" style={{ margin: '0 18px 14px' }} onClick={e => e.stopPropagation()}>
          {error}
        </p>
      )}
    </div>
  )
}

function parse(wb, filename) {
  const resumen    = parseResumen(wb)
  const estimacion = parseEstimacion(wb)
  const perfiles   = parseAnexos(wb)
  return { ...resumen, ...estimacion, perfiles, filename }
}

function parseResumen(wb) {
  if (!wb.SheetNames.includes('RESUMEN')) throw new Error('Hoja RESUMEN no encontrada')

  const ws   = wb.Sheets['RESUMEN']
  const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: null })

  const clienteCell = ws['B7']
  const cliente = clienteCell?.v ? String(clienteCell.v).trim() : ''

  let fsHorasFallback = 0, fsPersonasFallback = 0, inDetalle = false
  for (const row of rows) {
    if (row[1] === 'DETALLE FULL STACK' && row[2] === 'HORAS') { inDetalle = true; continue }
    if (!inDetalle) continue
    if (row[1] === 'TOTALES FULL STACK') { inDetalle = false; continue }
    const h = Math.round(typeof row[2] === 'number' ? row[2] : (parseFloat(String(row[2]) || '0') || 0))
    const p = Math.round(typeof row[3] === 'number' ? row[3] : (parseFloat(String(row[3]) || '0') || 0))
    if (h > 0) { fsHorasFallback += h; fsPersonasFallback = Math.max(fsPersonasFallback, p) }
  }

  const torres = []
  let inTorres = false
  for (const row of rows) {
    if (row[1] === 'TORRE' && row[2] === 'Horas') { inTorres = true; continue }
    if (!inTorres) continue
    if (!row[1] || String(row[1]).includes('TOTALES')) break

    const rawNombre = String(row[1]).trim()
    if (!rawNombre) continue

    const nombre = TORRE_RESUMEN_MAP[rawNombre]
      || rawNombre.replace(/^Torre\s+/i, '').toUpperCase()

    let horas = Math.round(typeof row[2] === 'number' ? row[2] : (parseFloat(String(row[2]) || '0') || 0))
    if (horas === 0 && nombre === 'FULLSTACK / DESARROLLO' && fsHorasFallback > 0)
      horas = fsHorasFallback

    const personasRaw = Math.round(typeof row[3] === 'number' ? row[3] : (parseFloat(String(row[3]) || '1') || 1))
    let personas = personasRaw
    if (horas === 0 && nombre === 'FULLSTACK / DESARROLLO' && fsPersonasFallback > 0)
      personas = fsPersonasFallback

    if (horas > 0) torres.push({ 
      nombre: String(nombre).trim(), 
      horas: Number(horas), 
      personas: Math.max(1, Number(personas)) 
    })
  }

  return { cliente: String(cliente).trim(), torres }
}

function parseEstimacion(wb) {
  const ws = wb.Sheets['Estimación'] || wb.Sheets['Estimacion']
  if (!ws) return { proyecto: '', consideraciones: [], fda: [], entregables: [] }

  const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: null })

  let proyecto = ''
  const cons = [], fdaItems = []
  const entMap = {}
  let currTorreEnt = null

  for (const row of rows) {
    if (row[0] === 'PROYECTO:' && row[1]) proyecto = String(row[1]).trim()

    const cellJ = row[9]
    if (cellJ != null && cellJ !== '' && cellJ !== undefined) {
      try {
        const texto = String(cellJ).trim()
        if (texto && texto !== 'Consideraciones' && texto !== 'Adicionales') {
          const lineas = texto.split('\n')
            .map(l => String(l).trim()).filter(l => l.length > 0)
            .filter(l => !/^(Riesgos|Consideraciones|Adicionales)\s*:?\s*$/i.test(l))
            .map(l => String(l).replace(/^\d+[\.\-]\s*/, '').trim())
            .filter(l => l.length > 10)
          for (const linea of lineas) { 
            const strLinea = String(linea).trim()
            if (strLinea && !cons.includes(strLinea)) cons.push(strLinea) 
          }
        }
      } catch (e) {
        console.warn('Error parsing cell J:', e)
      }
    }

    const cellK = row[10]
    if (cellK != null && cellK !== '' && cellK !== undefined) {
      try {
        const texto = String(cellK).trim()
        if (texto && !/^(Fuera del Alcance|FDA)\s*:?\s*$/i.test(texto)) {
          const partes = texto.split('.').map(p => String(p).trim()).filter(p => p.length > 5)
          for (const parte of partes) {
            const item = parte.endsWith('.') ? String(parte) : String(parte) + '.'
            if (!fdaItems.includes(item)) fdaItems.push(item)
          }
        }
      } catch (e) {
        console.warn('Error parsing cell K:', e)
      }
    }

    const cellM = row[12]
    if (cellM != null && cellM !== '' && cellM !== undefined) {
      try {
        const textoM = String(cellM).trim()
        if (/^Entregables?\s+por\s+torre\s*$/i.test(textoM)) {
          const cellA = row[0] != null ? String(row[0]).trim() : ''
          const m = cellA.match(/TORRE\s+(.+?)\s*[-–]/i)
          if (m) {
            const rawTorre = m[1].trim()
            currTorreEnt = TORRE_RESUMEN_MAP['Torre ' + rawTorre] || rawTorre.toUpperCase()
          }
        } else if (currTorreEnt && textoM.length > 3) {
          if (!entMap[currTorreEnt]) entMap[currTorreEnt] = []
          const strTextoM = String(textoM).trim()
          if (strTextoM && !entMap[currTorreEnt].includes(strTextoM)) entMap[currTorreEnt].push(strTextoM)
        }
      } catch (e) {
        console.warn('Error parsing cell M:', e)
      }
    }
  }

  const entregables = Object.entries(entMap).map(([torre, items]) => ({ 
    torre: String(torre).trim(), 
    items: items.map(i => String(i).trim()).filter(i => i.length > 0)
  }))
  return { 
    proyecto: String(proyecto).trim(), 
    consideraciones: cons.map(c => String(c).trim()).filter(c => c.length > 0), 
    fda: fdaItems.map(f => String(f).trim()).filter(f => f.length > 0), 
    entregables 
  }
}

function parseAnexos(wb) {
  const ws = wb.Sheets['Anexos']
  if (!ws) return []
  return XLSX.utils.sheet_to_json(ws, { header: 1, defval: null })
    .slice(1)
    .filter(r => {
      const cell0 = r[0] != null ? String(r[0]).trim() : ''
      return cell0 && cell0 !== 'TORRE' && cell0 !== 'TOTALES PROYECTO' && cell0 !== 'DIAGRAMAS'
    })
    .filter(r => r[1] != null && String(r[1]).trim() !== '')
    .map(r => {
      try {
        return {
          torre:     String(r[0] ?? '').trim().replace(/^Torre\s+/i, '').replace(/^TORRE\s+/i, ''),
          perfil:    String(r[1] ?? '').trim(),
          seniority: String(r[2] ?? '').trim(),
          personas:  typeof r[3] === 'number' ? Math.max(1, r[3]) : (parseFloat(String(r[3]) || '1') || 1),
          horas:     typeof r[4] === 'number' ? r[4] : (parseFloat(String(r[4] || '0')) || 0),
        }
      } catch (e) {
        console.warn('Error parsing anexo row:', r, e)
        return null
      }
    })
    .filter(item => item !== null && item.perfil.length > 0)
}
