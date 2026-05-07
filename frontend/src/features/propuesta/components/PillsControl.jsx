const SECTIONS = [
  { key: 'entregables',     icon: '📦', label: 'Entregables',        desc: 'Lista de productos y documentos a entregar al cliente.' },
  { key: 'perfiles',        icon: '👥', label: 'Perfiles',           desc: 'Roles y responsabilidades del equipo del proyecto.' },
  { key: 'consideraciones', icon: '📋', label: 'Consideraciones',    desc: 'Supuestos, restricciones y condiciones del proyecto.' },
  { key: 'fda',             icon: '🚫', label: 'Fuera del Alcance',  desc: 'Elementos explícitamente excluidos del proyecto.' },
]

export default function PillsControl({ opciones, onToggle, incluirQa, onToggleQa, excelVacio }) {
  const activeTags = SECTIONS.filter(s => opciones[s.key]).map(s => s.label)
  if (incluirQa) activeTags.push('QA')

  return (
    <div>
      <div className="slist">
        {SECTIONS.map(({ key, icon, label, desc }) => {
          const on = opciones[key]
          return (
            <div key={key} className={`srow${on ? ' is-yes' : ''}`}>
              <div className="stop">
                <div className="sico">{icon}</div>
                <div className="smeta">
                  <div className="sname">{label}</div>
                  <div className="sdesc">{desc}</div>
                  <div className={`sbadge${on ? ' show' : ''}`}>✦ Genéricos activados</div>
                </div>
                <div className={`pill${on ? ' on' : ''}`} onClick={() => onToggle(key)}>
                  <div className="pill-knob" />
                  <div className="pill-labs">
                    <span className="pno">NO</span>
                    <span className="psi">SÍ</span>
                  </div>
                </div>
              </div>
            </div>
          )
        })}

        <div className={`srow${incluirQa ? ' is-yes' : ''}`}>
          <div className="stop">
            <div className="sico">🧪</div>
            <div className="smeta">
              <div className="sname">Incluir QA</div>
              <div className="sdesc">¿El proyecto incluye pruebas de calidad?</div>
              <div className={`sbadge${incluirQa ? ' show' : ''}`}>✦ QA activado</div>
            </div>
            <div className={`pill${incluirQa ? ' on' : ''}`} onClick={onToggleQa}>
              <div className="pill-knob" />
              <div className="pill-labs">
                <span className="pno">NO</span>
                <span className="psi">SÍ</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mtags-wrap">
        <div className="mtags-label">Con genéricos activados</div>
        <div className="mtags">
          {activeTags.length === 0 ? (
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontStyle: 'italic' }}>
              Ninguna sección con genéricos
            </span>
          ) : (
            activeTags.map(t => <span key={t} className="mtag">{t}</span>)
          )}
        </div>
      </div>
    </div>
  )
}
