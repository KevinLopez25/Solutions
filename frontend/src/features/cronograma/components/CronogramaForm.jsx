import { useState, useRef } from 'react'
import * as XLSX from 'xlsx'
import { clasificarProductividad, generarCronograma } from '../services/cronogramaService'
import { useDownload } from '../../../shared/hooks/useDownload'

export default function CronogramaForm() {
  const inputRef               = useRef(null)
  const [parsed, setParsed]    = useState(null)
  const [filename, setFilename] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading]  = useState(false)
  const [error, setError]      = useState(null)
  const [horasSemanales, setHorasSemanales] = useState(42)
  const [productivityReview, setProductivityReview] = useState(null)
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
      const review = await clasificarProductividad(parsed.roles)
      const nonProductive = review.filter(profile => !profile.productivo)
      if (nonProductive.length > 0) {
        setProductivityReview(review)
        return
      }
      await downloadCronograma(parsed.actividades)
    } catch (err) {
      setError(err?.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  async function downloadCronograma(actividades) {
    const result = await generarCronograma({
      proyecto:    parsed.proyecto,
      cliente:     parsed.cliente,
      roles:       parsed.roles,
      actividades,
      horas_semanales: Math.max(1, Number(horasSemanales) || 42),
    })
    download(
      result.content_b64,
      result.filename,
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
  }

  async function confirmProductivity() {
    if (!productivityReview || !parsed) return
    setLoading(true)
    setError(null)
    try {
      const productiveByTower = new Map()
      for (const profile of productivityReview) {
        if (!profile.productivo) continue
        const tower = normalizarTorre(profile.torre)
        productiveByTower.set(
          tower,
          (productiveByTower.get(tower) || 0) + Math.max(1, Number(profile.personas) || 1),
        )
      }
      const actividades = parsed.actividades.map(activity => ({
        ...activity,
        personas: productiveByTower.get(normalizarTorre(activity.torre)) || 1,
      }))
      setProductivityReview(null)
      await downloadCronograma(actividades)
    } catch (err) {
      setError(err?.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  function toggleProductive(index) {
    setProductivityReview(current => current.map((profile, i) => (
      i === index ? { ...profile, productivo: !profile.productivo } : profile
    )))
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

      <div className="xdetail-card" style={{ marginBottom: '12px' }}>
        <div className="xdetail-head">
          <span>Parámetros del cronograma</span>
        </div>
        <div className="xdetail-body">
          <label htmlFor="cronograma-weekly-hours" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
            <span>Horas laborables por semana</span>
            <input
              id="cronograma-weekly-hours"
              type="number"
              min="1"
              step="1"
              value={horasSemanales}
              onChange={e => setHorasSemanales(e.target.value)}
              style={{ width: '88px', padding: '7px 9px' }}
            />
          </label>
        </div>
      </div>

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

      {productivityReview && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="productivity-review-title"
          style={{ position: 'fixed', inset: 0, zIndex: 20, background: 'rgba(0, 0, 0, .62)', display: 'grid', placeItems: 'center', padding: 20 }}
        >
          <div style={{ width: 'min(560px, 100%)', maxHeight: '90vh', overflow: 'auto', background: 'var(--panel, #17231c)', border: '1px solid rgba(46, 204, 113, .35)', borderRadius: 12, padding: 24, color: 'var(--white, #fff)' }}>
            <h2 id="productivity-review-title" style={{ margin: '0 0 8px' }}>Revisión de perfiles</h2>
            <p style={{ margin: '0 0 18px', color: 'var(--muted, #aab7ad)', lineHeight: 1.45 }}>
              La IA detectó perfiles que normalmente no desarrollan directamente. Decide si cada uno debe contar para reducir la duración de su torre.
            </p>
            <div style={{ display: 'grid', gap: 10 }}>
              {productivityReview.map((profile, index) => (
                <div key={`${profile.indice}-${profile.perfil}`} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, padding: 12, border: '1px solid rgba(255,255,255,.12)', borderRadius: 8 }}>
                  <div style={{ minWidth: 0 }}>
                    <strong>{profile.perfil}</strong>
                    <div style={{ fontSize: 12, color: 'var(--muted, #aab7ad)', marginTop: 4 }}>
                      {profile.torre || 'Torre no especificada'} · {profile.personas} persona(s)
                    </div>
                    {!profile.productivo && profile.explicacion && (
                      <div style={{ fontSize: 12, color: '#f0c674', marginTop: 5 }}>{profile.explicacion}</div>
                    )}
                  </div>
                  {!profile.productivo ? (
                    <button type="button" onClick={() => toggleProductive(index)} className="btn-secondary" style={{ whiteSpace: 'nowrap' }}>
                      Agregar como productivo
                    </button>
                  ) : (
                    <button type="button" onClick={() => toggleProductive(index)} className="btn-gen" style={{ whiteSpace: 'nowrap', padding: '8px 12px' }}>
                      Productivo
                    </button>
                  )}
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
              <button type="button" className="btn-secondary" onClick={() => setProductivityReview(null)} disabled={loading}>
                Cancelar
              </button>
              <button type="button" className="btn-gen" onClick={confirmProductivity} disabled={loading}>
                {loading ? 'Generando...' : 'Continuar y generar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Parseo del Excel ────────────────────────────────────────────────────────

function parseExcel(wb) {
  const resumen = parseResumen(wb)
  const roles   = parseAnexos(wb)
  const personasPorTorre = new Map()
  for (const rol of roles) {
    const torre = normalizarTorre(rol.torre)
    personasPorTorre.set(torre, (personasPorTorre.get(torre) || 0) + rol.personas)
  }
  const actividades = resumen.actividades.map(actividad => ({
    ...actividad,
    personas: personasPorTorre.get(normalizarTorre(actividad.torre)) || 1,
  }))
  return { ...resumen, actividades, roles }
}

function normalizarTorre(nombre) {
  return String(nombre || '').replace(/^torre\s+/i, '').trim().toLowerCase()
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
      personas: Math.max(1, Math.round(parseNumber(r[3]) || 1)),
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
