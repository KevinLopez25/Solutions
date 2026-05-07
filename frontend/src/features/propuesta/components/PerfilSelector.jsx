import { useState, useEffect } from 'react'
import { getPerfilesCatalog } from '../services/propuestaService'

export default function PerfilSelector({ selected, onAdd, onRemove, torres = [] }) {
  const [catalog, setCatalog] = useState([])
  const [query, setQuery]     = useState('')
  const [filtered, setFiltered] = useState([])
  const [open, setOpen]       = useState(false)

  useEffect(() => {
    getPerfilesCatalog().then(setCatalog).catch(console.error)
  }, [])

  useEffect(() => {
    const q = query.trim().toLowerCase()
    if (!q) { setFiltered([]); setOpen(false); return }
    const results = catalog.filter(p => p.rol.toLowerCase().includes(q)).slice(0, 50)
    setFiltered(results)
    setOpen(results.length > 0)
  }, [query, catalog])

  function pick(p) {
    onAdd({ rol: p.rol, desc: p.descripcion })
    setQuery('')
    setOpen(false)
  }

  return (
    <div className="perfil-selector">
      <p className="perfil-count">
        {catalog.length} perfiles disponibles
        {torres.length > 0 ? ` · Torres: ${torres.slice(0, 3).join(', ')}${torres.length > 3 ? '…' : ''}` : ''}
      </p>

      <div className="perfil-search-wrap">
        <input
          type="text"
          className="perfil-search-input"
          placeholder="Buscar perfil en el catálogo..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => filtered.length > 0 && setOpen(true)}
          onBlur={() => setTimeout(() => setOpen(false), 150)}
          autoComplete="off"
        />
        <div className={`perfil-results-dropdown${open ? ' open' : ''}`}>
          {filtered.map(p => (
            <div key={p.id} className="perfil-result-item" onMouseDown={() => pick(p)}>
              <strong>{p.rol}</strong>
              <small>{p.descripcion}</small>
            </div>
          ))}
        </div>
      </div>

      {selected.map((p, i) => (
        <div key={i} className="perfil-chip">
          <span className="perfil-chip-rol">{p.rol}</span>
          <button className="perfil-chip-rm" onClick={() => onRemove(i)}>&times;</button>
        </div>
      ))}
    </div>
  )
}
