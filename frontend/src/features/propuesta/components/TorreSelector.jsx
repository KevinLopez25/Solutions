import { TORRE_ICONS } from '../../../core/constants'

export default function TorreSelector({ torres, selected, onToggle, showHours = false }) {
  if (!torres || torres.length === 0) return null

  if (showHours) {
    const maxHrs = Math.max(...torres.map(t => t.horas || 0), 1)
    return (
      <div className="xdetail-card" style={{ marginTop: '14px' }}>
        <div className="xdetail-head">
          <span>Torres del proyecto</span>
          <span style={{ color: 'var(--g)', fontSize: '10px', fontWeight: 700 }}>
            Haz clic para activar/desactivar
          </span>
        </div>
        <div className="xdetail-body">
          {torres.map((t) => {
            const nombre    = typeof t === 'string' ? t : t.nombre
            const horas     = typeof t === 'object' ? t.horas : null
            const isSelected = selected.includes(nombre)
            const icon      = TORRE_ICONS[nombre] || '🏗️'
            const pct       = horas ? Math.round((horas / maxHrs) * 100) : 0

            return (
              <div
                key={nombre}
                className="xdetail-row"
                onClick={() => onToggle(nombre)}
                style={{ opacity: isSelected ? 1 : 0.45 }}
              >
                <div className="xdetail-row-left">
                  <span>{icon}</span>
                  <span>{nombre}</span>
                  {isSelected && (
                    <span style={{ color: 'var(--g)', fontSize: '11px', fontWeight: 700 }}>✓</span>
                  )}
                </div>
                {horas != null && (
                  <div className="xdetail-bar-wrap">
                    <div className="xdetail-bar">
                      <div className="xdetail-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="xdetail-hrs">{horas} hrs</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="torre-chips-row">
      {torres.map((t) => {
        const nombre    = typeof t === 'string' ? t : t.nombre
        const isSelected = selected.includes(nombre)
        const icon      = TORRE_ICONS[nombre] || '🏗️'
        return (
          <div
            key={nombre}
            className={`torre-sel-chip${isSelected ? ' on' : ''}`}
            onClick={() => onToggle(nombre)}
          >
            {icon} {nombre}
          </div>
        )
      })}
    </div>
  )
}
