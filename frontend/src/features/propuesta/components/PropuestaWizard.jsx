import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FILIALES, FILIAL_LABELS, FILIAL_CODES, TORRES_ALL, TORRE_ICONS, PILL_LABELS } from '../../../core/constants'
import { usePropuesta } from '../hooks/usePropuesta'
import ExcelUploader from './ExcelUploader'
import TorreSelector from './TorreSelector'
import PerfilSelector from './PerfilSelector'
import PillsControl from './PillsControl'

const STEPS     = ['Modo', 'Excel', 'Torres', 'Filial', 'Secciones', 'Resumen']
const PROG_TEXT = ['Elige el tipo', 'Sube el Excel', 'Revisa los datos', 'Elige la filial', 'Configura secciones', 'Genera el documento']
const TOTAL     = STEPS.length - 1

export default function PropuestaWizard({ onDraftGenerated, proposalDraft, reviewRequested, onOpenChat }) {
  const navigate = useNavigate()
  const [step, setStep]               = useState(0)
  const [modoPerfiles, setModoPerfiles] = useState('catalogo')
  const [manualRol, setManualRol]     = useState('')
  const [manualDesc, setManualDesc]   = useState('')

  const {
    filial, setFilial,
    excelData, setExcelData,
    torresSeleccionadas, setTorres,
    perfilesManuales, setPerfiles,
    opciones, togglePill,
    incluirQa, setIncluirQa,
    loading, error,
    generate,
    downloadProposal,
  } = usePropuesta()

  const excelVacio = !excelData || (excelData.torres?.length ?? 0) === 0
  const totalHrs   = excelData?.torres?.reduce((s, t) => s + (t.horas || 0), 0) ?? 0

  function next() { setStep(s => Math.min(s + 1, TOTAL)) }
  function back() { setStep(s => Math.max(s - 1, 0)) }

  function handleExcelParsed(data) {
    if (!data) return
    try {
      // Sanitizar los datos del Excel
      const sanitized = {
        cliente:         String(data.cliente || '').trim(),
        proyecto:        String(data.proyecto || '').trim(),
        filename:        String(data.filename || '').trim(),
        torres:          (Array.isArray(data.torres) ? data.torres : [])
          .filter(t => t && typeof t === 'object')
          .map(t => ({
            nombre:   String(t.nombre || '').trim(),
            horas:    Math.round(Number(t.horas) || 0),
            personas: Math.max(1, Math.round(Number(t.personas) || 1)),
          }))
          .filter(t => t.nombre.length > 0),
        perfiles:        (Array.isArray(data.perfiles) ? data.perfiles : [])
          .filter(p => p && typeof p === 'object')
          .map(p => ({
            torre:     String(p.torre || '').trim(),
            perfil:    String(p.perfil || '').trim(),
            seniority: String(p.seniority || '').trim(),
            personas:  Number(p.personas) || 1,
          }))
          .filter(p => p.perfil.length > 0),
        consideraciones: (Array.isArray(data.consideraciones) ? data.consideraciones : [])
          .map(c => String(c).trim())
          .filter(c => c.length > 0),
        fda:             (Array.isArray(data.fda) ? data.fda : [])
          .map(f => String(f).trim())
          .filter(f => f.length > 0),
        entregables:     (Array.isArray(data.entregables) ? data.entregables : [])
          .map(e => ({
            torre: String(e.torre || '').trim(),
            items: (Array.isArray(e.items) ? e.items : [])
              .map(i => String(i).trim())
              .filter(i => i.length > 0),
          }))
          .filter(e => e.torre.length > 0 && e.items.length > 0),
      }
      setExcelData(sanitized)
      if (sanitized.torres?.length) setTorres(sanitized.torres.map(t => t.nombre))
    } catch (err) {
      console.error('Error sanitizing Excel data:', err)
    }
  }

  function toggleTorre(nombre) {
    setTorres(prev => prev.includes(nombre) ? prev.filter(t => t !== nombre) : [...prev, nombre])
  }

  function addManual() {
    const rol = manualRol.trim()
    if (!rol) return
    setPerfiles(prev => [...prev, { rol, desc: manualDesc.trim() }])
    setManualRol('')
    setManualDesc('')
  }

  async function handleGenerate() {
    const efectivos = excelVacio && modoPerfiles === 'manual' ? perfilesManuales : []
    const draft = await generate(efectivos)
    if (onDraftGenerated) {
      onDraftGenerated(draft)
    }
  }

  function handleDownload() {
    if (proposalDraft) {
      downloadProposal(proposalDraft)
    }
  }

  const pct = (step / TOTAL) * 100

  return (
    <div>
      {/* ── Sticky header ── */}
      <header className="hdr">
        <Link to="/" className="logo" style={{ textDecoration: 'none' }}>
          <div className="logo-gem">P</div>
          <div>
            <div className="logo-name">Periferia</div>
            <div className="logo-sub">Generador RFI</div>
          </div>
        </Link>

        <div className="hsteps">
          {STEPS.map((s, i) => (
            <span key={s} style={{ display: 'contents' }}>
              {i > 0 && <div className="hs-sep" />}
              <div className={`hs${i === step ? ' sa' : i < step ? ' sd' : ''}`}>
                <div className="hs-n">{i < step ? '✓' : i + 1}</div>
                {s}
              </div>
            </span>
          ))}
        </div>

        <Link to="/cronograma" style={{ fontSize: '10px', color: 'var(--muted)', textDecoration: 'none', letterSpacing: '.06em', textTransform: 'uppercase', fontFamily: 'Syne,sans-serif', fontWeight: 700 }}>
          Cronograma →
        </Link>
      </header>

      {/* ── Content ── */}
      <div className="wrap">

        {/* STEP 0: MODO */}
        {step === 0 && (
          <div className="pstep active">
            <div className="eyebrow"><div className="el" />Bienvenido<div className="elr" /></div>
            <h1 className="step-h">¿Qué quieres<br /><em>generar?</em></h1>
            <p className="step-p">Selecciona el tipo de documento que deseas crear para tu proyecto.</p>

            <div className="mode-grid">
              <div className="mode-card ppt on" onClick={next}>
                <div className="mode-card-ico">📊</div>
                <div className="mode-card-name">Propuesta PPT</div>
                <div className="mode-card-desc">Genera la presentación de propuesta con secciones y perfiles del proyecto</div>
              </div>
              <div className="mode-card crono" onClick={() => navigate('/cronograma')}>
                <div className="mode-card-ico">📅</div>
                <div className="mode-card-name">Cronograma</div>
                <div className="mode-card-desc">Genera el cronograma del proyecto a partir del Excel de estimación</div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 1: EXCEL */}
        {step === 1 && (
          <div className="pstep active">
            <div className="eyebrow"><div className="el" />Paso 1 de 5<div className="elr" /></div>
            <h1 className="step-h">Carga el<br /><em>documento</em></h1>
            <p className="step-p">Sube el Excel de estimación del proyecto. Leeremos su contenido automáticamente para construir la propuesta.</p>
            <ExcelUploader onParsed={handleExcelParsed} />
          </div>
        )}

        {/* STEP 2: TORRES + PERFILES (o resumen si Excel tiene datos) */}
        {step === 2 && (
          <div className="pstep active">
            <div className="eyebrow"><div className="el" />Paso 2 de 5<div className="elr" /></div>

            {!excelVacio ? (
              <>
                <h1 className="step-h">Contenido del<br /><em>documento</em></h1>
                <p className="step-p">Esto es lo que encontramos en el Excel. Activa o desactiva torres según necesites.</p>

                <div className="xsummary-banner">
                  <span className="xsummary-banner-icon">📎</span>
                  <div className="xsummary-banner-text">
                    Archivo: <strong>{excelData?.filename || '—'}</strong>
                    {' — '}<strong>{totalHrs}</strong> horas totales en{' '}
                    <strong>{excelData?.torres?.length ?? 0}</strong> torres
                  </div>
                </div>

                <div className="xsummary-grid">
                  <div className="xstat">
                    <span className="xstat-icon">⏱️</span>
                    <div className="xstat-val">{totalHrs}<span> hrs</span></div>
                    <div className="xstat-label">Total horas</div>
                  </div>
                  <div className="xstat">
                    <span className="xstat-icon">🏗️</span>
                    <div className="xstat-val">{excelData?.torres?.length ?? 0}<span> torres</span></div>
                    <div className="xstat-label">Torres detectadas</div>
                  </div>
                  <div className="xstat">
                    <span className="xstat-icon">👤</span>
                    <div className="xstat-val">{excelData?.perfiles?.length ?? 0}<span> roles</span></div>
                    <div className="xstat-label">Perfiles identificados</div>
                  </div>
                  <div className="xstat">
                    <span className="xstat-icon">📋</span>
                    <div className="xstat-val" style={{ fontSize: excelData?.cliente ? '16px' : undefined }}>
                      {excelData?.cliente || '—'}
                    </div>
                    <div className="xstat-label">Cliente</div>
                  </div>
                </div>

                <TorreSelector
                  torres={excelData.torres}
                  selected={torresSeleccionadas}
                  onToggle={toggleTorre}
                  showHours={true}
                />
              </>
            ) : (
              <>
                <h1 className="step-h">Torres y<br /><em>perfiles</em></h1>
                <p className="step-p">No detectamos datos con horas en el Excel. Elige las torres del proyecto y cómo manejar los perfiles.</p>

                <TorreSelector
                  torres={TORRES_ALL}
                  selected={torresSeleccionadas}
                  onToggle={toggleTorre}
                  showHours={false}
                />

                <div className="perfil-mode-wrap">
                  <div className="perfil-mode-label">Modo de perfiles</div>
                  <div className="perfil-mode-chips">
                    <div
                      className={`perfil-mode-chip${modoPerfiles === 'catalogo' ? ' on' : ''}`}
                      onClick={() => setModoPerfiles('catalogo')}
                    >
                      📚 Catálogo completo
                    </div>
                    <div
                      className={`perfil-mode-chip${modoPerfiles === 'manual' ? ' on' : ''}`}
                      onClick={() => setModoPerfiles('manual')}
                    >
                      🔍 Elegir perfiles
                    </div>
                  </div>
                </div>

                {modoPerfiles === 'catalogo' ? (
                  <div className="perfil-catalog-notice">
                    <span>📚</span>
                    <div>
                      <strong>Catálogo completo activado</strong>
                      <p>Se usarán los perfiles genéricos del catálogo base de Periferia para las torres seleccionadas.</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <PerfilSelector
                      selected={perfilesManuales}
                      onAdd={p => setPerfiles(prev => [...prev, p])}
                      onRemove={i => setPerfiles(prev => prev.filter((_, idx) => idx !== i))}
                      torres={torresSeleccionadas}
                    />
                    <div className="perfil-manual-form">
                      <div className="perfil-manual-title">Agregar perfil manualmente</div>
                      <input
                        className="perfil-search-input"
                        placeholder="Rol del perfil..."
                        value={manualRol}
                        onChange={e => setManualRol(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && addManual()}
                      />
                      <textarea
                        className="perfil-manual-desc"
                        placeholder="Descripción (opcional)..."
                        value={manualDesc}
                        onChange={e => setManualDesc(e.target.value)}
                        rows={2}
                      />
                      <button
                        className="perfil-manual-btn"
                        onClick={addManual}
                        disabled={!manualRol.trim()}
                      >
                        + Agregar perfil
                      </button>
                    </div>
                  </>
                )}
              </>
            )}

            {torresSeleccionadas.length > 0 && (
              <div className="qa-row-full">
                <span className="qa-row-label">🧪 ¿El proyecto incluye pruebas de calidad (QA)?</span>
                <div className={`pill${incluirQa ? ' on' : ''}`} onClick={() => setIncluirQa(v => !v)}>
                  <div className="pill-knob" />
                  <div className="pill-labs">
                    <span className="pno">NO</span>
                    <span className="psi">SÍ</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* STEP 3: FILIAL */}
        {step === 3 && (
          <div className="pstep active">
            <div className="eyebrow"><div className="el" />Paso 3 de 5<div className="elr" /></div>
            <h1 className="step-h">¿Cuál es<br /><em>la filial?</em></h1>
            <p className="step-p">Selecciona la empresa bajo la que se emite esta propuesta.</p>
            <div className="fgrid">
              {FILIALES.map(f => (
                <div key={f} className={`fcard${filial === f ? ' on' : ''}`} onClick={() => setFilial(f)}>
                  <div className="fchk">✓</div>
                  <div className={`fbadge ${f}`}>{FILIAL_CODES[f]}</div>
                  <div className="fname">{FILIAL_LABELS[f]}</div>
                  <div className="fcode">{FILIAL_CODES[f]}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* STEP 4: SECCIONES */}
        {step === 4 && (
          <div className="pstep active">
            <div className="eyebrow"><div className="el" />Paso 4 de 5<div className="elr" /></div>
            {!excelVacio ? (
              <>
                <h1 className="step-h">Contenido<br /><em>genérico</em></h1>
                <p className="step-p">Las secciones se generarán con la información del Excel. Si activas el genérico, <em style={{ fontStyle: 'normal', color: 'var(--white)' }}>se enriquecerán adicionalmente</em> con contenido estándar de Periferia.</p>
                <div className="generic-notice">
                  <span className="generic-notice-icon">💡</span>
                  <div className="generic-notice-text">
                    <strong>NO activado</strong> → la sección se genera únicamente con los datos del Excel.<br />
                    <strong>SÍ activado</strong> → se añade contenido genérico de Periferia además de los datos del Excel.
                  </div>
                </div>
              </>
            ) : (
              <>
                <h1 className="step-h">¿Qué secciones<br /><em>incluir?</em></h1>
                <p className="step-p">Como el Excel estaba vacío, todo el contenido vendrá del catálogo genérico de Periferia. Activa las secciones que quieres incluir en la propuesta.</p>
              </>
            )}
            <PillsControl
              opciones={opciones}
              onToggle={togglePill}
              incluirQa={incluirQa}
              onToggleQa={() => setIncluirQa(v => !v)}
              excelVacio={excelVacio}
            />
          </div>
        )}

        {/* STEP 5: RESUMEN */}
        {step === 5 && (
          <div className="pstep active">
            <div className="eyebrow"><div className="el" />Resumen final<div className="elr" /></div>
            <h1 className="step-h">Revisa y<br /><em>genera</em></h1>
            <p className="step-p">Confirma todo antes de generar el documento.</p>

            <div className="sum-card">
              <div className="sum-head"><span className="sum-head-title">Configuración general</span></div>
              <div className="sum-body">
                <div className="sr">
                  <span className="sr-l"><span>🏢</span>Filial</span>
                  <span className="stag y">{FILIAL_LABELS[filial] || filial}</span>
                </div>
                <div className="sr">
                  <span className="sr-l"><span>📄</span>Documento</span>
                  <span className="stag b">{excelData?.filename || 'Sin Excel'}</span>
                </div>
                <div className="sr">
                  <span className="sr-l"><span>🏗️</span>Torres</span>
                  <span className="stag b">{torresSeleccionadas.length} seleccionadas</span>
                </div>
                {excelData?.cliente && (
                  <div className="sr">
                    <span className="sr-l"><span>👤</span>Cliente</span>
                    <span className="stag n">{excelData.cliente}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="sum-card">
              <div className="sum-head"><span className="sum-head-title">Datos del documento</span></div>
              <div className="sum-body">
                <div className="sr">
                  <span className="sr-l"><span>⏱️</span>Total horas</span>
                  <span className="stag b">{totalHrs > 0 ? `${totalHrs} hrs` : 'N/A'}</span>
                </div>
                <div className="sr">
                  <span className="sr-l"><span>👤</span>Perfiles</span>
                  <span className="stag b">{(excelData?.perfiles?.length ?? 0) + perfilesManuales.length} roles</span>
                </div>
                <div className="sr">
                  <span className="sr-l"><span>📊</span>Fuente</span>
                  <span className="stag b">{excelData?.torres?.length ? 'Del Excel' : 'Genéricos'}</span>
                </div>
                <div className="sr">
                  <span className="sr-l"><span>🔬</span>QA</span>
                  <span className={`stag${incluirQa ? ' y' : ' n'}`}>{incluirQa ? 'Con QA' : 'Sin QA'}</span>
                </div>
                {excelVacio && (
                  <div className="sr">
                    <span className="sr-l"><span>👥</span>Modo perfiles</span>
                    <span className="stag b">{modoPerfiles === 'catalogo' ? 'Catálogo completo' : `Manual (${perfilesManuales.length})`}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="sum-card">
              <div className="sum-head"><span className="sum-head-title">Secciones y genéricos</span></div>
              <div className="sum-body">
                {Object.entries(opciones).map(([key, val]) => (
                  <div key={key} className="sr">
                    <span className="sr-l"><span>📌</span>{PILL_LABELS[key]}</span>
                    <span className={`stag${val ? ' y' : ' n'}`}>{val ? '✦ Con genéricos' : 'Solo del Excel'}</span>
                  </div>
                ))}
              </div>
            </div>

            {torresSeleccionadas.length > 0 && (
              <div className="sum-card">
                <div className="sum-head"><span className="sum-head-title">Torres seleccionadas</span></div>
                <div className="sum-body">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '7px', paddingTop: '4px' }}>
                    {torresSeleccionadas.map(t => (
                      <span key={t} className="mtag">{TORRE_ICONS[t] || '🏗️'} {t}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {perfilesManuales.length > 0 && excelVacio && modoPerfiles === 'manual' && (
              <div className="sum-card">
                <div className="sum-head"><span className="sum-head-title">Perfiles manuales</span></div>
                <div className="sum-body">
                  {perfilesManuales.map((p, i) => (
                    <div key={i} className="sr">
                      <span className="sr-l"><span>👤</span>{p.rol}</span>
                      {p.desc && <span className="stag n">{p.desc.slice(0, 32)}{p.desc.length > 32 ? '…' : ''}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {proposalDraft && (
              <div className="review-block">
                <div className="review-title">Propuesta generada</div>
                <div className="review-text">La propuesta está lista. Antes de descargarla, revisa en el chat con IA y solicita los cambios que quieras.</div>
                <div className="review-actions">
                  <button className="btn-secondary" type="button" onClick={onOpenChat}>
                    Abrir chat para revisión
                  </button>
                  <button
                    className="btn-gen"
                    type="button"
                    disabled={!reviewRequested || loading}
                    onClick={handleDownload}
                  >
                    {reviewRequested ? '⬇ Descargar propuesta' : '🔍 Revisión IA requerida'}
                  </button>
                </div>
                {!reviewRequested && (
                  <div className="review-note">Solicita la revisión en el chat antes de descargar la propuesta.</div>
                )}
              </div>
            )}

            {error && <p className="err-txt">{error}</p>}

            <div className="gen-block">
              <span className="gen-emoji">🚀</span>
              <div className="gen-t">Todo listo</div>
              <div className="gen-s">El documento se generará con los datos del Excel más los genéricos seleccionados.</div>
              <button className="btn-gen" onClick={handleGenerate} disabled={loading}>
                {loading ? '⏳ Generando...' : proposalDraft ? '⬇ Regenerar propuesta' : '⬇ Generar documento'}
              </button>
            </div>
          </div>
        )}

      </div>

      {/* ── Fixed bottom nav ── */}
      <div className="nav">
        <button className={`btn-n btn-back${step === 0 ? ' hidden' : ''}`} onClick={back}>
          ← Atrás
        </button>

        <div className="prog-wrap">
          <div className="prog-bar">
            <div className="prog-fill" style={{ width: `${pct}%` }} />
          </div>
          <div className="prog-txt">{PROG_TEXT[step]}</div>
        </div>

        {step < TOTAL && (
          <button className="btn-n btn-fwd" onClick={next}>
            Siguiente →
          </button>
        )}
        {step === TOTAL && (
          <button className="btn-n btn-fwd" onClick={() => setStep(0)}>
            ← Volver al inicio
          </button>
        )}
      </div>
    </div>
  )
}
