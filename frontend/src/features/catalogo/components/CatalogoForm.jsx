import { useState } from 'react'

export default function CatalogoForm({ fields, onSubmit, submitLabel = 'Guardar' }) {
  const initial = Object.fromEntries(fields.map(f => [f.key, f.default ?? '']))
  const [values, setValues] = useState(initial)

  function handleChange(key, value) {
    setValues(prev => ({ ...prev, [key]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit?.(values)
    setValues(initial)
  }

  return (
    <form className="catalogo-form" onSubmit={handleSubmit}>
      {fields.map(f => (
        <label key={f.key}>
          {f.label}
          {f.type === 'textarea' ? (
            <textarea
              value={values[f.key]}
              onChange={e => handleChange(f.key, e.target.value)}
              required={f.required}
            />
          ) : (
            <input
              type={f.type || 'text'}
              value={values[f.key]}
              onChange={e => handleChange(f.key, e.target.value)}
              required={f.required}
            />
          )}
        </label>
      ))}
      <button type="submit" className="btn-primary">{submitLabel}</button>
    </form>
  )
}
