import React, { useEffect, useState } from 'react'

export default function QualityTestPanel({ open, onClose }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (!open) return

    setLoading(true)
    setError(null)
    setResult(null)

    const base = (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.DEV)
      ? 'http://localhost:8000'
      : ''

    fetch(`${base}/api/v1/quality/run-tests`, { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        setResult(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(String(err))
        setLoading(false)
      })
  }, [open])

  if (!open) return null

  return (
    <div className="quality-panel-backdrop" onClick={onClose}>
      <div className="quality-panel" onClick={(event) => event.stopPropagation()}>
        <div className="quality-panel-header">
          <div>
            <div className="quality-panel-title">Pruebas de calidad del proyecto</div>
            <div className="quality-panel-subtitle">Se ejecutan y se muestran en tiempo real cuando presionas el botón.</div>
          </div>
          <button className="quality-close-btn" onClick={onClose} aria-label="Cerrar panel de pruebas">✕</button>
        </div>

        <div className="quality-summary">
          <div className="quality-summary-item">
            <span className="quality-summary-label">Total</span>
            <strong>{result && result.tests_summary ? result.tests_summary.split(',')[0] : (loading ? 'Ejecutando...' : 'Sin datos')}</strong>
          </div>
          <div className="quality-summary-item">
            <span className="quality-summary-label">Resultado</span>
            <span className={`quality-status-badge ${result && result.success ? 'success' : 'error'}`}>{result ? (result.success ? 'OK' : 'Falló') : (loading ? '...' : '—')}</span>
          </div>
          <div className="quality-summary-item">
            <span className="quality-summary-label">Actualizado</span>
            <strong>{result ? 'Ahora mismo' : '—'}</strong>
          </div>
        </div>

        <div className="quality-section">
          <div className="quality-section-title">Salida de las pruebas</div>
          {loading && <div className="quality-text">Ejecutando pruebas en el servidor, espera por favor...</div>}
          {error && <div className="quality-text" style={{ color: 'var(--danger, #ff6b6b)' }}>Error de conexión: {error}</div>}

          {result && (
            <div>
              {result.stderr && <div className="quality-text" style={{ color: 'var(--danger, #ff6b6b)' }}><strong>Error:</strong> {result.stderr}</div>}
              <div className="quality-text"><strong>Resumen:</strong> {result.tests_summary || 'No disponible'}</div>

              <div className="quality-section-title" style={{ marginTop: '12px' }}>Cobertura</div>
              <div className="quality-text">Se muestra la tabla de cobertura generada por pytest.</div>
              <div style={{ overflowX: 'auto', marginTop: 8 }}>
                <table className="quality-coverage-table">
                  <thead>
                    <tr>
                      <th>Archivo</th>
                      <th>Stmts</th>
                      <th>Miss</th>
                      <th>Cover</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.coverage && result.coverage.length > 0 ? (
                      result.coverage.map((r) => (
                        <tr key={r.file}>
                          <td style={{ whiteSpace: 'nowrap' }}>{r.file}</td>
                          <td>{r.stmts}</td>
                          <td>{r.miss}</td>
                          <td>{r.cover}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4}>No se encontró información de cobertura en la salida.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div className="quality-section-title" style={{ marginTop: '12px' }}>Logs completos</div>
              <pre className="quality-logs" style={{ whiteSpace: 'pre-wrap', maxHeight: '240px', overflow: 'auto' }}>{result.stdout}</pre>
              {result.stderr && <pre className="quality-logs" style={{ whiteSpace: 'pre-wrap', color: 'var(--danger, #ff6b6b)' }}>{result.stderr}</pre>}
            </div>
          )}
        </div>

        <div className="quality-section quality-footer">
          <div className="quality-footer-text">Este panel muestra el resultado de correr `pytest` en el backend. No realiza cambios en el sistema.</div>
        </div>
      </div>
    </div>
  )
}
