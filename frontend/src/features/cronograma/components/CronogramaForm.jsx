import { useState, useRef } from 'react'
import * as XLSX from 'xlsx'
import { generarCronograma } from '../services/cronogramaService'
import { useDownload } from '../../../shared/hooks/useDownload'

export default function CronogramaForm() {
  const inputRef               = useRef(null)
  const [parsed, setParsed]    = useState(null)
  const [filename, setFilename] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading]  = useState(false)
  const [error, setError]      = useState(null)
  const { download }           = useDownload()

  function process(file) {
    if (!file) return
    setError(null)
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const wb = XLSX.read(ev.target.result, { type: 'array' })
        setParsed(parseExcel(wb))
        setFilename(file.name)
      } catch (err) {
        setError(err?.message || String(err))
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
    setParsed(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
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
      setError(err?.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  const totalHrs = parsed?.actividades?.reduce((s, a) => s + (a.horas || 0), 0) ?? 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
      <div className="eyebrow"><div className="el" />Cronograma<div className="elr" /></div>
      <h1 className="step-h">Genera el<br /><em>cronograma</em></h1>
      <p className="step-p">
        Sube el Excel de estimación — el cronograma se genera automáticamente
        a partir de las torres y horas del RESUMEN.
      </p>

      {/* Upload zone */}
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

      {/* Preview */}
      {parsed && (
        <>
          {/* Stats */}
          <div className="xsummary-grid" style={{ marginTop: '20px' }}>
            <div className="xstat">
              <span className="xstat-icon">⏱️</span>
              <div className="xstat-val">{totalHrs}<span> hrs</span></div>
              <div className="xstat-label">Total horas</div>
            </div>
            <div className="xstat">
              <span className="xstat-icon">🏗️</span>
              <div className="xstat-val">{parsed.actividades.length}<span> torres</span></div>
              <div className="xstat-label">Detectadas</div>
            </div>
            <div className="xstat">
              <span className="xstat-icon">👥</span>
              <div className="xstat-val">{parsed.roles.length}<span> roles</span></div>
              <div className="xstat-label">Perfiles</div>
            </div>
            <div className="xstat">
              <span className="xstat-icon">📋</span>
              <div className="xstat-val" style={{ fontSize: parsed.cliente ? '14px' : undefined }}>
                {parsed.cliente || '—'}
              </div>
              <div className="xstat-label">Cliente</div>
            </div>
          </div>

          {/* Torre breakdown */}
          <div className="xdetail-card" style={{ marginTop: '12px' }}>
            <div className="xdetail-head">
              <span>Torres detectadas</span>
            </div>
            <div className="xdetail-body">
              {parsed.actividades.map((a, i) => {
                const maxH = Math.max(...parsed.actividades.map(x => x.horas || 0), 1)
                const pct  = Math.round(((a.horas || 0) / maxH) * 100)
                return (
                  <div key={i} className="xdetail-row" style={{ cursor: 'default' }}>
                    <div className="xdetail-row-left">
                      <span>🏗️</span>
                      <span>{a.torre}</span>
                    </div>
                    <div className="xdetail-bar-wrap">
                      <div className="xdetail-bar">
                        <div className="xdetail-bar-fill" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="xdetail-hrs">{a.horas} hrs</span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Generate */}
          <div className="gen-block">
            <span className="gen-emoji">📅</span>
            <div className="gen-t">Listo para generar</div>
            <div className="gen-s">
              Se descargará el cronograma en formato Excel (.xlsx) con todas las actividades y fechas.
            </div>
            <button className="btn-gen" onClick={handleGenerate} disabled={loading}>
              {loading ? '⏳ Generando...' : '⬇ Descargar cronograma'}
            </button>
          </div>
        </>
      )}
    </div>
  )
}

// ── Parseo del Excel ────────────────────────────────────────────────────────

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

  const actividades = rows
    .filter(r => Array.isArray(r) && r[1] && typeof r[1] === 'string' && String(r[1]).trim().toLowerCase().startsWith('torre'))
    .map(r => ({
      torre:   String(r[1]).replace(/^torre\s*/i, '').trim(),
      horas:   parseNumber(r[2]),
      personas: 1,
    }))
    .filter(a => a.torre && a.horas > 0)

  if (actividades.length === 0)
    throw new Error('No se encontraron torres con horas en la hoja RESUMEN')

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
      personas:  Math.max(1, Math.round(parseNumber(r[3]) || 1)),
      torre:     String(r[0] || '').trim(),
    }))
}

function parseNumber(value) {
  if (typeof value === 'number') return value
  const n = parseFloat(String(value || '').trim().replace(/\s+/g, '').replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}
