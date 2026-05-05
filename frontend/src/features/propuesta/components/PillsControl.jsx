import { PILLS } from '../../../core/constants'
import Toggle from '../../../shared/components/Toggle'

export default function PillsControl({ opciones, onToggle, incluirQa, onToggleQa }) {
  return (
    <div className="pills-panel">
      <h3>Opciones genéricas</h3>
      {PILLS.map(({ key, label }) => (
        <Toggle
          key={key}
          label={label}
          checked={opciones[key]}
          onChange={() => onToggle(key)}
        />
      ))}
      <Toggle label="Incluir QA" checked={incluirQa} onChange={onToggleQa} />
    </div>
  )
}
