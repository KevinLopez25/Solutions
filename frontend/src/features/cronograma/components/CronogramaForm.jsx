import { useState, useRef } from 'react'
import * as XLSX from 'xlsx'
import { generarCronograma } from '../services/cronogramaService'
import { useDownload } from '../../../shared/hooks/useDownload'

export default function CronogramaForm() {
  const inputRef              = useRef(null)
  const [parsed, setParsed]   = useState(null)   // { proyecto, cliente, actividades, roles }
  const [filename, setFilename] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const { download }          = useDownload()

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const wb = XLSX.read(ev.target.result, { type: 'array' })
        setParsed(parseExcel(wb))
        setFilename(file.name)
      } catch (err) {
        setError(err?.message || (typeof err === 'string' ? err : JSON.stringify(err)))
      }
    }
    reader.readAsArrayBuffer(file)
  }

  async function handleGenerate() {
    if (!parsed) return
    setLoading(true)
    setError(null)
    try {
      const result = await generarCronograma({
        proyecto:    parsed.proyecto,
        cliente:     parsed.cliente,
        roles:       parsed.roles,
        actividades: parsed.actividades,
      })
      download(
        result.content_b64,
        result.filename,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      )
    } catch (err) {
      setError(err?.message || (typeof err === 'string' ? err : JSON.stringify(err)))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="cronograma-form">
      <h2>Generar Cronograma</h2>
      <p className="form-subtitle">
        Sube el Excel de estimación — el cronograma se genera automáticamente
        a partir de las torres y horas del RESUMEN.
      </p>

      {/* Upload */}
      <div className="upload-zone" onClick={() => inputRef.current?.click()}>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={handleFile}
          style={{ display: 'none' }}
        />
        {filename
          ? <p className="success-text">📄 {filename}</p>
          : <p className="upload-hint">Haz clic para seleccionar el Excel de estimación</p>
        }
      </div>

      {error && <p className="error-text">{error}</p>}

      {/* Preview */}
      {parsed && (
        <div className="cronograma-preview">
          <div className="preview-meta">
            <span><strong>Proyecto:</strong> {parsed.proyecto || '—'}</span>
            <span><strong>Cliente:</strong>  {parsed.cliente  || '—'}</span>
          </div>

          <div className="preview-cols">
            <div className="preview-col">
              <h3>Torres / Actividades ({parsed.actividades.length})</h3>
              <ul>
                {parsed.actividades.map((a, i) => (
                  <li key={i}>
                    <span className="preview-chip">{a.torre}</span>
                    <span className="preview-hours">{a.horas} h</span>
                  </li>
                ))}
              </ul>
            </div>

            {parsed.roles.length > 0 && (
              <div className="preview-col">
                <h3>Perfiles / Roles ({parsed.roles.length})</h3>
                <ul>
                  {parsed.roles.map((r, i) => (
                    <li key={i}>
                      <span className="preview-chip">{r.perfil}</span>
                      {r.torre && <span className="preview-torre">{r.torre}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <button
            className="btn-primary"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? 'Generando...' : 'Descargar Cronograma .xlsx'}
          </button>
        </div>
      )}
    </div>
  )
}

// ── Parseo del Excel de estimación ────────────────────────────────────────────

function parseExcel(wb) {
  const resumen = parseResumen(wb)
  const roles   = parseAnexos(wb)
  return { ...resumen, roles }
}

function parseResumen(wb) {
  const ws = wb.Sheets['RESUMEN']
  if (!ws) throw new Error('Hoja RESUMEN no encontrada en el Excel')

  const rows = XLSX.utils.sheet_to_json(ws, { header: 1 })

  const proyecto = String(rows.find(r => r[0] === 'Proyecto')?.[1] || '')
  const cliente  = String(rows.find(r => r[0] === 'Cliente')?.[1]  || '')

  // Torres: columna B contiene la torre y columna C las horas
  const actividades = rows
    .filter(r => Array.isArray(r) && r[1] && typeof r[1] === 'string' && String(r[1]).trim().toLowerCase().startsWith('torre'))
    .map(r => {
      const torre = String(r[1]).replace(/^torre\s*/i, '').trim()
      const horas = parseNumber(r[2])
      return {
        torre,
        horas,
        personas: 1,
      }
    })
    .filter(a => a.torre && a.horas > 0)

  if (actividades.length === 0) {
    throw new Error('No se encontraron torres con horas en la hoja RESUMEN')
  }

  return { proyecto, cliente, actividades }
}

function parseAnexos(wb) {
  const ws = wb.Sheets['Anexos']
  if (!ws) return []

  return XLSX.utils.sheet_to_json(ws, { header: 1 })
    .slice(1)
    .filter(r => Array.isArray(r) && r[1])
    .map(r => ({
      perfil:    String(r[1]).trim(),
      seniority: String(r[2] || '').trim(),
      personas:  1,
      torre:     String(r[0] || '').trim(),
    }))
}

function parseNumber(value) {
  if (typeof value === 'number') return value
  const normalized = String(value || '').trim().replace(/\s+/g, '').replace(',', '.')
  const parsed = parseFloat(normalized)
  return Number.isFinite(parsed) ? parsed : 0
}