export default function TorreSelector({ torres, selected, onToggle }) {
  return (
    <div className="torre-selector">
      <h3>Torres activas</h3>
      <div className="torre-grid">
        {torres.map((t) => {
          const nombre = typeof t === 'string' ? t : t.nombre
          const isSelected = selected.includes(nombre)
          return (
            <button
              key={nombre}
              className={`torre-chip ${isSelected ? 'active' : ''}`}
              onClick={() => onToggle(nombre)}
              type="button"
            >
              {nombre}
            </button>
          )
        })}
      </div>
    </div>
  )
}
