export default function Toggle({ label, checked, onChange }) {
  return (
    <label className="toggle-row">
      <span>{label}</span>
      <div className={`toggle-switch ${checked ? 'on' : 'off'}`} onClick={onChange}>
        <div className="toggle-thumb" />
      </div>
    </label>
  )
}
