import { useState, useEffect } from 'react'
import { getPerfilesCatalog } from '../services/propuestaService'

export default function PerfilSelector({ selected, onAdd, onRemove, torres = [] }) {
  const [catalog, setCatalog] = useState([])
  const [query, setQuery]     = useState('')
  const [filtered, setFiltered] = useState([])

  useEffect(() => {
    getPerfilesCatalog().then(setCatalog).catch(console.error)
  }, [])

  useEffect(() => {
    const q = query.trim().toLowerCase()
    if (!q) {
      setFiltered(catalog.slice(0, 50))
      return
    }
    setFiltered(catalog.filter(p => p.rol.toLowerCase().includes(q)).slice(0, 50))
  }, [query, catalog])

  const availableCount = catalog.length
  const towerLabel = torres.length > 0 ? `Torres: ${torres.join(', ')}` : 'Todas las torres'

  return (
    <div className="perfil-selector">
      <div className="profile-top">
        <div>
          <h3>Perfiles de la base de datos</h3>
          <p className="profile-meta">{availableCount} perfiles disponibles · {towerLabel}</p>
        </div>
      </div>

      <input
        type="text"
        placeholder="Buscar perfil..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        className="search-input"
      />

      <ul className="dropdown">
        {filtered.map(p => (
          <li key={p.id} onClick={() => { onAdd({ rol: p.rol, desc: p.descripcion }); setQuery('') }}>
            <strong>{p.rol}</strong>
            <span>{p.descripcion}</span>
          </li>
        ))}
        {filtered.length === 0 && (
          <li className="dropdown-empty">No se encontraron perfiles</li>
        )}
      </ul>

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
