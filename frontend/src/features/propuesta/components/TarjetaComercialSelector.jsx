import { useEffect, useRef, useState } from 'react'
import { buscarTarjetasComerciales, listarPaisesTarjetas } from '../services/propuestaService'

const PAIS_ORDER = ['colombia', 'ecuador', 'mexico', 'panama', 'peru']

export default function TarjetaComercialSelector({ value, onChange }) {
  const [paises, setPaises] = useState([])
  const [pais, setPais] = useState('')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const debounceRef = useRef(null)

  useEffect(() => {
    listarPaisesTarjetas()
      .then((data) => {
        const ordered = PAIS_ORDER
          .map((s) => data.find((p) => p.slug === s))
          .filter(Boolean)
        setPaises(ordered.length ? ordered : data)
      })
      .catch(() => setPaises([]))
    return () => clearTimeout(debounceRef.current)
  }, [])

  function selectPais(slug) {
    setPais(slug)
    setQuery('')
    setResults([])
    setOpen(false)
    setPending(null)
    setError('')
  }

  function search(raw) {
    const q = (raw || '').trim()
    setQuery(raw)
    clearTimeout(debounceRef.current)
    if (!pais || !q) { setResults([]); setOpen(false); return }
    debounceRef.current = setTimeout(async () => {
      setLoading(true); setError('')
      try {
        const data = await buscarTarjetasComerciales(q, pais)
        setResults(data)
        setOpen(data.length > 0)
        if (data.length === 1) setPending(data[0])
      } catch (err) {
        setError(err?.message || 'No se pudo buscar.'); setOpen(false)
      } finally { setLoading(false) }
    }, 250)
  }

  function pick(item) {
    setPending(item)
    setOpen(false)
    setQuery('')
  }

  function confirmAdd() {
    if (pending) onChange && onChange({ ...pending, pais })
    setPending(null)
  }

  return (
    <div className="tarjeta-selector">
      {/* ── Selector de país con banderas ── */}
      <div className="tarjeta-pais-grid">
        {paises.map((p) => (
          <button
            key={p.slug}
            type="button"
            className={`tarjeta-pais-chip${pais === p.slug ? ' on' : ''}`}
            onClick={() => selectPais(p.slug)}
            title={p.nombre}
          >
            <span className="tarjeta-bandera">{p.bandera}</span>
            <span className="tarjeta-pais-nombre">{p.nombre}</span>
          </button>
        ))}
      </div>

      <div className="perfil-search-wrap">
        <input
          type="text"
          className="perfil-search-input"
          placeholder={pais ? '🔍 Buscar comercial (lupa)…' : 'Primero selecciona un país…'}
          value={query}
          onChange={(e) => search(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          disabled={!pais}
          autoComplete="off"
        />
        {loading && <div className="perfil-search-loading">Buscando…</div>}
        {open && (
          <div className="perfil-results-dropdown open tarjeta-dropdown">
            {results.map((r) => (
              <div key={r.archivo} className="perfil-result-item" onMouseDown={() => pick(r)}>
                <strong>{r.bandera || '👤'} {r.nombre}</strong>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <p style={{ fontSize: 12, color: '#f87171', marginTop: 4 }}>{error}</p>}

      {pending && (
        <div className="perfil-chip" style={{ marginTop: 8 }}>
          <span className="perfil-chip-rol">👤 {pending.nombre}</span>
          <button className="perfil-chip-rm" onClick={() => setPending(null)} title="Quitar selección">&times;</button>
        </div>
      )}

      <button
        type="button"
        className="perfil-manual-btn"
        style={{ marginTop: 8, width: '100%' }}
        onClick={confirmAdd}
        disabled={!pending}
      >
        ➕ Añadir tarjeta comercial
      </button>

      {value && (
        <div className="perfil-chip" style={{ marginTop: 8, background: 'linear-gradient(135deg,#1a3a2a,#0d2818)' }}>
          <span className="perfil-chip-rol">
            ✅ Añadida: {value.bandera ? value.bandera + ' ' : '👤 '}{value.nombre}
          </span>
          <button className="perfil-chip-rm" onClick={() => onChange && onChange(null)} title="Quitar tarjeta">&times;</button>
        </div>
      )}
    </div>
  )
}

