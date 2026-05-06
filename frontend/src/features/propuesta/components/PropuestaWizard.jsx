import { useState } from 'react'
import { FILIALES, FILIAL_LABELS } from '../../../core/constants'
import { usePropuesta } from '../hooks/usePropuesta'
import ExcelUploader from './ExcelUploader'
import TorreSelector from './TorreSelector'
import PerfilSelector from './PerfilSelector'
import PillsControl from './PillsControl'

const STEPS = ['Filial', 'Excel', 'Torres', 'Perfiles', 'Opciones', 'Generar']

export default function PropuestaWizard() {
  const [step, setStep] = useState(0)
  const {
    filial, setFilial,
    excelData, setExcelData,
    torresSeleccionadas, setTorres,
    perfilesManuales, setPerfiles,
    opciones, togglePill,
    incluirQa, setIncluirQa,
    loading, error,
    generate,
  } = usePropuesta()

  function next() { setStep(s => Math.min(s + 1, STEPS.length - 1)) }
  function back() { setStep(s => Math.max(s - 1, 0)) }

  function handleExcelParsed(data) {
    setExcelData(data)
    setTorres(data.torres?.map(t => t.nombre) || [])
  }

  function toggleTorre(nombre) {
    setTorres(prev =>
      prev.includes(nombre) ? prev.filter(t => t !== nombre) : [...prev, nombre]
    )
  }

  function addPerfil(p) { setPerfiles(prev => [...prev, p]) }
  function removePerfil(i) { setPerfiles(prev => prev.filter((_, idx) => idx !== i)) }

  async function handleGenerate() {
    await generate()
  }

  return (
    <div className="wizard">
      <div className="wizard-steps">
        {STEPS.map((s, i) => (
          <span key={s} className={`step ${i === step ? 'active' : i < step ? 'done' : ''}`}>
            {s}
          </span>
        ))}
      </div>

      <div className="wizard-body">
        {step === 0 && (
          <div>
            <h2>Selecciona la filial</h2>
            <div className="filial-options">
              {FILIALES.map(f => (
                <button
                  key={f}
                  className={`filial-btn ${filial === f ? 'selected' : ''}`}
                  onClick={() => setFilial(f)}
                >
                  {FILIAL_LABELS[f]}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 1 && (
          <div>
            <h2>Cargar Excel de estimación</h2>
            <ExcelUploader onParsed={handleExcelParsed} />
            {excelData && (
              <p className="success-text">
                Excel cargado: {excelData.proyecto} — {excelData.cliente}
              </p>
            )}
          </div>
        )}

        {step === 2 && (
          <>
            <div className="summary-cards">
              <div className="summary-card">
                <span className="summary-label">Torres estimadas</span>
                <strong>{excelData?.torres?.length ?? 0}</strong>
              </div>
              <div className="summary-card">
                <span className="summary-label">Horas estimadas</span>
                <strong>{excelData?.torres?.reduce((sum, item) => sum + (item?.horas || 0), 0) ?? 0}</strong>
              </div>
              <div className="summary-card">
                <span className="summary-label">Proyecto</span>
                <strong>{excelData?.proyecto || 'No cargado'}</strong>
              </div>
            </div>

            <TorreSelector
              torres={excelData?.torres || torresSeleccionadas}
              selected={torresSeleccionadas}
              onToggle={toggleTorre}
            />
          </>
        )}

        {step === 3 && (
          <PerfilSelector
            selected={perfilesManuales}
            onAdd={addPerfil}
            onRemove={removePerfil}
            torres={torresSeleccionadas}
          />
        )}

        {step === 4 && (
          <PillsControl
            opciones={opciones}
            onToggle={togglePill}
            incluirQa={incluirQa}
            onToggleQa={() => setIncluirQa(v => !v)}
          />
        )}

        {step === 5 && (
          <div className="generate-step">
            <h2>Generar propuesta</h2>
            <p>Filial: <strong>{FILIAL_LABELS[filial]}</strong></p>
            <p>Torres: <strong>{torresSeleccionadas.join(', ') || '—'}</strong></p>
            {error && <p className="error-text">{error}</p>}
            <button
              className="btn-primary"
              onClick={handleGenerate}
              disabled={loading}
            >
              {loading ? 'Generando...' : 'Descargar Propuesta .pptx'}
            </button>
          </div>
        )}
      </div>

      <div className="wizard-nav">
        {step > 0 && <button className="btn-secondary" onClick={back}>Atrás</button>}
        {step < STEPS.length - 1 && (
          <button className="btn-primary" onClick={next}>Siguiente</button>
        )}
      </div>
    </div>
  )
}
