import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FILIALES, FILIAL_LABELS, FILIAL_CODES, TORRES_ALL, TORRE_ICONS, PILL_LABELS } from '../../../core/constants'
import { usePropuesta } from '../hooks/usePropuesta'
import { reemplazarLogo } from '../../ai/services/aiService'
import { clasificarProductividad } from '../../ai/services/aiService'
import { subirPlantillaTemplate } from '../services/propuestaService'
import ExcelUploader from './ExcelUploader'
import TorreSelector from './TorreSelector'
import PerfilSelector from './PerfilSelector'
import PillsControl from './PillsControl'
import TarjetaComercialSelector from './TarjetaComercialSelector'

const STEPS = ['Modo', 'Excel', 'Torres', 'Filial', 'Secciones', 'Resumen']
const PROG_TEXT = ['Elige el tipo', 'Sube el Excel', 'Revisa los datos', 'Elige la filial', 'Configura secciones', 'Genera el documento']
const TOTAL = STEPS.length - 1

export default function PropuestaWizard({ onDraftGenerated, proposalDraft, reviewRequested, onOpenChat }) {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [modoPerfiles, setModoPerfiles] = useState('catalogo')
  const [manualRol, setManualRol] = useState('')
  const [manualDesc, setManualDesc] = useState('')
  const [logoFile, setLogoFile] = useState(null) // { b64, mimeType, name }
  const [applyingLogo, setApplyingLogo] = useState(false)
  const [logoMsg, setLogoMsg] = useState(null) // { ok: bool, text: string }
  const [templateMsg, setTemplateMsg] = useState(null)
  const [uploadingTemplate, setUploadingTemplate] = useState(false)
  const [tarjetaComercial, setTarjetaComercial] = useState(null)
  const {
    filial, setFilial,
    excelData, setExcelData,
    torresSeleccionadas, setTorres,
    perfilesManuales, setPerfiles,
    opciones, togglePill,
    incluirQa, setIncluirQa,
    asIsEnabled, setAsIsEnabled,
    asIsDescription, setAsIsDescription,
    horasSemanales, setHorasSemanales,
    cronogramaPorPerfiles, setCronogramaPorPerfiles,
    loading, error,
    generate,
    downloadProposal,
    iaAlcance, setIaAlcance,
    templateName, setTemplateName,
    applyingTemplate,
    applyTemplateToProposal,
  } = usePropuesta()

  const excelVacio = !excelData || (excelData.torres?.length ?? 0) === 0
  const totalHrs = excelData?.torres?.reduce((s, t) => s + (t.horas || 0), 0) ?? 0

  function next() { setStep(s => Math.min(s + 1, TOTAL)) }
  function back() { setStep(s => Math.max(s - 1, 0)) }

  function handleExcelParsed(data) {
    if (!data) return
    try {
      // Sanitizar los datos del Excel
      const sanitized = {
        cliente: String(data.cliente || '').trim(),
        proyecto: String(data.proyecto || '').trim(),
        filename: String(data.filename || '').trim(),
        torres: (Array.isArray(data.torres) ? data.torres : [])
          .filter(t => t && typeof t === 'object')
          .map(t => ({
            nombre: String(t.nombre || '').trim(),
            horas: Math.round(Number(t.horas) || 0),
            personas: Math.max(1, Math.round(Number(t.personas) || 1)),
          }))
          .filter(t => t.nombre.length > 0),
        perfiles: (Array.isArray(data.perfiles) ? data.perfiles : [])
          .filter(p => p && typeof p === 'object')
          .map(p => ({
            torre: String(p.torre || '').trim(),
            perfil: String(p.perfil || '').trim(),
            seniority: String(p.seniority || '').trim(),
            personas: Number(p.personas) || 1,
          }))
          .filter(p => p.perfil.length > 0),
        consideraciones: (Array.isArray(data.consideraciones) ? data.consideraciones : [])
          .map(c => String(c).trim())
          .filter(c => c.length > 0),
        fda: (Array.isArray(data.fda) ? data.fda : [])
          .map(f => String(f).trim())
          .filter(f => f.length > 0),
        entregables: (Array.isArray(data.entregables) ? data.entregables : [])
          .map(e => ({
            torre: String(e.torre || '').trim(),
            items: (Array.isArray(e.items) ? e.items : [])
              .map(i => String(i).trim())
              .filter(i => i.length > 0),
          }))
          .filter(e => e.torre.length > 0 && e.items.length > 0),
        alcances: (Array.isArray(data.alcances) ? data.alcances : [])
          .map(a => ({
            torre: String(a.torre || '').trim(),
            items: (Array.isArray(a.items) ? a.items : [])
              .map(i => ({
                titulo:      String(i.titulo || '').trim(),
                descripcion: String(i.descripcion || '').trim(),
              }))
              .filter(i => i.titulo.length > 0),
          }))
          .filter(a => a.torre.length > 0),
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

  async function handleApplyLogo() {
    if (!logoFile || !proposalDraft || applyingLogo) return
    setApplyingLogo(true)
    setLogoMsg(null)
    try {
      const { content_b64 } = await reemplazarLogo({
        content_b64: proposalDraft.content_b64,
        logo_b64: logoFile.b64,
        logo_mime: logoFile.mimeType,
      })
      onDraftGenerated({ ...proposalDraft, content_b64 })
      setLogoMsg({ ok: true, text: 'Logo aplicado correctamente. Descarga la propuesta para verlo.' })
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'Error al aplicar el logo.'
      setLogoMsg({ ok: false, text: detail })
    } finally {
      setApplyingLogo(false)
    }
  }

  function handleLogoChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const b64 = reader.result.split(',')[1]
      setLogoFile({ b64, mimeType: file.type || 'image/png', name: file.name })
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  async function handleTemplateUpload(e) {
    const file = e.target.files?.[0]
    if (!file || !filial) return

    setUploadingTemplate(true)
    setTemplateMsg(null)
    try {
      // Usamos el nombre original del archivo (incluye extensión .pptx)
      const originalName = file.name
      const result = await subirPlantillaTemplate({
        file,
        filial,
        section: 'default',
        templateName: originalName,
      })
      // Guardamos el nombre exacto que devolvió el backend
      const savedName = result.template_name
      setTemplateName(savedName)
      setTemplateMsg({ ok: true, text: `Plantilla cargada: ${savedName}` })
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.message || 'No se pudo cargar la plantilla.'
      setTemplateMsg({ ok: false, text: detail })
    } finally {
      setUploadingTemplate(false)
      e.target.value = ''
    }
  }

  async function handleGenerate() {
    const efectivos = excelVacio && modoPerfiles === 'manual' ? perfilesManuales : []
    let draft = await generate(efectivos, false, tarjetaComercial)
    if (!draft) return

    if (logoFile) {
      setApplyingLogo(true)
      try {
        const { content_b64 } = await reemplazarLogo({
          content_b64: draft.content_b64,
          logo_b64: logoFile.b64,
          logo_mime: logoFile.mimeType,
        })
        draft = { ...draft, content_b64 }
      } catch (err) {
        const detail = err?.response?.data?.detail || err?.message || 'Error al aplicar el logo.'
        setLogoMsg({ ok: false, text: detail })
      } finally {
        setApplyingLogo(false)
      }
    }

    if (onDraftGenerated) onDraftGenerated(draft)
    setProductivityReview(null)
  }

  function toggleProductive(index) {
    setProductivityReview(current => current.map((profile, i) => (
      i === index ? { ...profile, productivo: !profile.productivo } : profile
    )))
  }

  function cancelProductivityReview() {
    setProductivityReview(null)
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
          <div className="logo-gem">
            <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ display: 'block', width: '100%', height: '100%', padding: 4 }}>
              {/* Cabeza del robot */}
              <rect x="9" y="7" width="14" height="10" rx="2.5" fill="currentColor"/>
              {/* Antenas */}
              <rect x="14" y="4" width="4" height="3" rx="1" fill="currentColor"/>
              <circle cx="16" cy="3" r="1.5" fill="currentColor" opacity="0.9"/>
              {/* Ojos */}
              <rect x="11" y="9" width="3.5" height="3" rx="1" fill="#000"/>
              <rect x="17.5" y="9" width="3.5" height="3" rx="1" fill="#000"/>
              {/* Pupilas */}
              <rect x="12.5" y="9.8" width="1.2" height="1.2" rx="0.6" fill="#00E676"/>
              <rect x="19" y="9.8" width="1.2" height="1.2" rx="0.6" fill="#00E676"/>
              {/* Boca sonrisa */}
              <path d="M12 14.5 Q16 17 20 14.5" stroke="#000" strokeWidth="1.2" strokeLinecap="round" fill="none"/>
              {/* Cuerpo */}
              <rect x="8" y="17" width="16" height="9" rx="2" fill="currentColor" opacity="0.85"/>
              {/* Panel central */}
              <rect x="13" y="19" width="6" height="5" rx="1" fill="#000" opacity="0.4"/>
              <circle cx="14.5" cy="20.5" r="0.6" fill="#00E676" opacity="0.8"/>
              <circle cx="16" cy="22.5" r="0.6" fill="#00E676" opacity="0.6"/>
              <circle cx="17.5" cy="20.5" r="0.6" fill="#00E676" opacity="0.8"/>
              {/* Brazos */}
              <rect x="4" y="11" width="4" height="2.5" rx="1.2" fill="currentColor" opacity="0.7"/>
              <rect x="24" y="11" width="4" height="2.5" rx="1.2" fill="currentColor" opacity="0.7"/>
            </svg>
          </div>
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
                <div className="sr" style={{ alignItems: 'center', gap: 12 }}>
                  <label className="sr-l" htmlFor="proposal-weekly-hours">
                    <span>🗓️</span>Horas laborables por semana
                  </label>
                  <input
                    id="proposal-weekly-hours"
                    type="number"
                    min="1"
                    step="1"
                    value={horasSemanales}
                    onChange={e => setHorasSemanales(e.target.value)}
                    style={{ width: 88, padding: '7px 9px' }}
                  />
                </div>
                <div className="sr" style={{ alignItems: 'center', gap: 12 }}>
                  <label className="sr-l" htmlFor="proposal-cronograma-by-profile">
                    <span>👤</span>Generar cronograma por perfiles
                  </label>
                  <input
                    id="proposal-cronograma-by-profile"
                    type="checkbox"
                    checked={cronogramaPorPerfiles}
                    onChange={e => setCronogramaPorPerfiles(e.target.checked)}
                  />
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

            <div className="sum-card">
              <div className="sum-head"><span className="sum-head-title">AS-IS y TO-BE</span></div>
              <div className="sum-body">
                <div className="sr" style={{ alignItems: 'center', gap: 12 }}>
                  <span className="sr-l">📝 Descargar con AS-IS y TO-BE</span>
                  <div className={`pill${asIsEnabled ? ' on' : ''}`} onClick={() => setAsIsEnabled((v) => !v)}>
                    <div className="pill-knob" />
                    <div className="pill-labs">
                      <span className="pno">NO</span>
                      <span className="psi">SÍ</span>
                    </div>
                  </div>
                </div>
                {asIsEnabled && (
                  <div style={{ marginTop: 12 }}>
                    <textarea
                      className="perfil-manual-desc"
                      placeholder="Describe de forma general el estado actual del cliente antes de la solución..."
                      value={asIsDescription}
                      onChange={(e) => setAsIsDescription(e.target.value)}
                      rows={4}
                    />
                    <p style={{ marginTop: 8, fontSize: 13, color: 'var(--muted)', lineHeight: 1.4 }}>
                      El estado actual se mejorará profesionalmente con IA y se insertará en AS-IS. TO-BE se generará internamente desde el contexto del Excel.
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="sum-card">
              <div className="sum-head">
                <span className="sum-head-title">ALCANCE</span>
              </div>

              <div className="sum-body">
                <div className="sr" style={{ alignItems: 'center', gap: 12 }}>
                  <span className="sr-l">📝 ALCANCE</span>

                  <div
                    className={`pill${iaAlcance ? ' on' : ''}`}
                    onClick={() => setIaAlcance((v) => !v)}
                  >
                    <div className="pill-knob" />

                    <div className="pill-labs">
                      <span className="pno">NO</span>
                      <span className="psi">SÍ</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {proposalDraft && (
              <div className="review-block">
                <div className="review-title">Propuesta generada</div>
                <div className="review-text">La propuesta está lista. Puedes descargarla directamente o revisarla con el asistente IA antes.</div>
                <div className="review-actions">
                  <button className="btn-secondary" type="button" onClick={handleDownload}>
                    ⬇ Descargar sin revisión
                  </button>
                  <button className="btn-secondary" type="button" onClick={onOpenChat}>
                    Revisar con IA
                  </button>
                  <button
                    className="btn-gen"
                    type="button"
                    disabled={!reviewRequested || loading}
                    onClick={handleDownload}
                  >
                    {reviewRequested ? '⬇ Descargar con cambios IA' : '🔍 Pendiente revisión IA'}
                  </button>
                </div>
              </div>
            )}

            {productivityReview && (
              <div
                role="dialog"
                aria-modal="true"
                aria-labelledby="proposal-productivity-title"
                style={{ position: 'fixed', inset: 0, zIndex: 30, background: 'rgba(0, 0, 0, .64)', display: 'grid', placeItems: 'center', padding: 20 }}
              >
                <div style={{ width: 'min(600px, 100%)', maxHeight: '90vh', overflow: 'auto', background: 'var(--panel, #17231c)', border: '1px solid rgba(46, 204, 113, .35)', borderRadius: 12, padding: 24, color: 'var(--white, #fff)' }}>
                  <h2 id="proposal-productivity-title" style={{ margin: '0 0 8px' }}>Revisión de perfiles del cronograma</h2>
                  <p style={{ margin: '0 0 18px', color: 'var(--muted, #aab7ad)', lineHeight: 1.45 }}>
                    La IA encontró perfiles que normalmente no desarrollan directamente. Puedes decidir cuáles deben contar para reducir la duración de su torre.
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
                        <button
                          type="button"
                          className={profile.productivo ? 'btn-gen' : 'btn-secondary'}
                          onClick={() => toggleProductive(index)}
                          style={{ whiteSpace: 'nowrap', padding: '8px 12px' }}
                        >
                          {profile.productivo ? 'Productivo' : 'Agregar como productivo'}
                        </button>
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20 }}>
                    <button type="button" className="btn-secondary" onClick={cancelProductivityReview}>Cancelar</button>
                    <button type="button" className="btn-gen" onClick={handleGenerate} disabled={loading}>
                      {loading ? 'Generando...' : 'Continuar y generar'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="sum-card">
              <div className="sum-head"><span className="sum-head-title">Plantillas de propuesta</span></div>
              <div className="sum-body">
                <div className="sr">
                  <span className="sr-l"><span>📄</span>Cargar nueva plantilla (.pptx)</span>
                  <label style={{ cursor: 'pointer' }}>
                    <input
                      id="template-upload"
                      type="file"
                      accept=".pptx,application/vnd.openxmlformats-officedocument.presentationml.presentation"
                      onChange={handleTemplateUpload}
                      style={{ display: 'none' }}
                    />
                    <span className="stag b" style={{ cursor: 'pointer' }}>
                      {uploadingTemplate ? 'Subiendo…' : '📂 Seleccionar archivo'}
                    </span>
                  </label>
                </div>
                {templateMsg && (
                  <p style={{ marginTop: 8, fontSize: 13, color: templateMsg.ok ? 'var(--accent)' : '#f87171' }}>
                    {templateMsg.ok ? '✅' : '⚠️'} {templateMsg.text}
                  </p>
                )}

                {/* Mostrar plantilla cargada y botón para aplicarla */}
                {templateName && (
                  <div style={{ marginTop: 12, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                    <div className="sr">
                      <span className="sr-l"><span>🎨</span>Plantilla activa</span>
                      <span className="stag y">{templateName}</span>
                    </div>
                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ marginTop: 10, width: '100%' }}
                      onClick={async () => {
                        const efectivos = excelVacio && modoPerfiles === 'manual' ? perfilesManuales : []
                        setTemplateMsg(null)
                        const draft = await applyTemplateToProposal(efectivos, tarjetaComercial)
                        if (draft) {
                          if (logoFile) {
                            try {
                              const { content_b64 } = await reemplazarLogo({
                                content_b64: draft.content_b64,
                                logo_b64: logoFile.b64,
                                logo_mime: logoFile.mimeType,
                              })
                              draft.content_b64 = content_b64
                            } catch (err) {
                              const detail = err?.response?.data?.detail || err?.message || 'Error al aplicar el logo.'
                              setLogoMsg({ ok: false, text: detail })
                            }
                          }
                          if (onDraftGenerated) onDraftGenerated(draft)
                          setTemplateMsg({ ok: true, text: '✅ Plantilla aplicada con éxito. La propuesta se regeneró con la nueva plantilla.' })
                        }
                      }}
                      disabled={applyingTemplate || loading}
                    >
                      {applyingTemplate || loading ? '⏳ Aplicando plantilla...' : '🎨 Aplicar plantilla a la propuesta'}
                    </button>
                    {applyingTemplate && (
                      <p style={{ marginTop: 8, fontSize: 13, color: 'var(--accent)' }}>
                        ⏳ Regenerando la propuesta con la plantilla seleccionada...
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {error && <p className="err-txt">{error}</p>}

            {/* ── Logo de la empresa ── */}
            <div className="sum-card">
              <div className="sum-head"><span className="sum-head-title">Logo de la empresa (opcional)</span></div>
              <div className="sum-body">
                <div className="sr">
                  <span className="sr-l"><span>🖼️</span>Se colocará en la primera diapositiva</span>
                  {logoFile ? (
                    <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="stag y">{logoFile.name}</span>
                      <button
                        type="button"
                        style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: 14, padding: 0 }}
                        onClick={() => { setLogoFile(null); setLogoMsg(null) }}
                      >✕</button>
                    </span>
                  ) : (
                    <label style={{ cursor: 'pointer' }}>
                      <input
                        type="file"
                        accept=".png,.jpg,.jpeg,.gif,.webp,.svg"
                        onChange={e => { setLogoMsg(null); handleLogoChange(e) }}
                        style={{ display: 'none' }}
                      />
                      <span className="stag b" style={{ cursor: 'pointer' }}>📂 Subir logo</span>
                    </label>
                  )}
                </div>

                {logoFile && (
                  <img
                    src={`data:${logoFile.mimeType};base64,${logoFile.b64}`}
                    alt="Logo preview"
                    style={{ maxHeight: 64, maxWidth: '100%', marginTop: 8, borderRadius: 6, objectFit: 'contain', display: 'block' }}
                  />
                )}

                {/* Botón para aplicar el logo a la propuesta ya generada */}
                {logoFile && proposalDraft && (
                  <button
                    type="button"
                    className="btn-secondary"
                    style={{ marginTop: 10, width: '100%' }}
                    onClick={handleApplyLogo}
                    disabled={applyingLogo}
                  >
                    {applyingLogo ? '🖼️ Aplicando logo...' : '🖼️ Aplicar logo a la propuesta'}
                  </button>
                )}

                {logoMsg && (
                  <p style={{ marginTop: 8, fontSize: 13, color: logoMsg.ok ? 'var(--accent)' : '#f87171' }}>
                    {logoMsg.ok ? '✅' : '⚠️'} {logoMsg.text}
                  </p>
                )}
              </div>
            </div>

            <div className="gen-block">
              <span className="gen-emoji">💳</span>
              <div className="gen-t">Tarjeta comercial</div>
              <div className="gen-s">Busca el nombre del comercial y añade su tarjeta. Se insertarán sus 2 slides después del slide 13.</div>
              <TarjetaComercialSelector
                value={tarjetaComercial}
                onChange={setTarjetaComercial}
              />
            </div>

            <div className="gen-block">
              <span className="gen-emoji">🚀</span>
              <div className="gen-t">Todo listo</div>
              <div className="gen-s">El documento se generará con los datos del Excel más los genéricos seleccionados.</div>
              <button className="btn-gen" onClick={handleGenerate} disabled={loading || applyingLogo}>
                {loading ? '⏳ Generando...' : applyingLogo ? '🖼️ Aplicando logo...' : proposalDraft ? '⬇ Regenerar propuesta' : '⬇ Generar documento'}
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
