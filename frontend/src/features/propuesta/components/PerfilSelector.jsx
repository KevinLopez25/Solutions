import { useState, useEffect } from 'react'
import { getPerfilesCatalog } from '../services/propuestaService'

export default function PerfilSelector({ selected, onAdd, onRemove }) {
  const [catalog, setCatalog] = useState([])
  const [query, setQuery]     = useState('')
  const [filtered, setFiltered] = useState([])

  useEffect(() => {
    getPerfilesCatalog().then(setCatalog).catch(console.error)
  }, [])

  useEffect(() => {
    if (!query.trim()) { setFiltered([]); return }
    const q = query.toLowerCase()
    setFiltered(catalog.filter(p => p.rol.toLowerCase().includes(q)).slice(0, 8))
  }, [query, catalog])

  return (
    <div className="perfil-selector">
      <h3>Perfiles manuales</h3>
      <input
        type="text"
        placeholder="Buscar perfil..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        className="search-input"
      />
      {filtered.length > 0 && (
        <ul className="dropdown">
          {filtered.map(p => (
            <li key={p.id} onClick={() => { onAdd({ rol: p.rol, desc: p.descripcion }); setQuery('') }}>
              <strong>{p.rol}</strong>
            </li>
          ))}
        </ul>
      )}
      {selected.length > 0 && (
        <div className="selected-chips">
          {selected.map((p, i) => (
            <span key={i} className="chip">
              {p.rol}
              <button onClick={() => onRemove(i)}>&times;</button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
