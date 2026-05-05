import { useState } from 'react'
import { generarCronograma } from '../services/cronogramaService'
import { useDownload } from '../../../shared/hooks/useDownload'

export default function CronogramaForm() {
  const [proyecto, setProyecto]       = useState('')
  const [cliente, setCliente]         = useState('')
  const [roles, setRoles]             = useState([{ perfil: '', seniority: '', personas: 1, torre: '' }])
  const [actividades, setActividades] = useState([{ torre: '', horas: 43, personas: 1 }])
  const [loading, setLoading]         = useState(false)
  const [error, setError]             = useState(null)
  const { download } = useDownload()

  function addRol() { setRoles(prev => [...prev, { perfil: '', seniority: '', personas: 1, torre: '' }]) }
  function addActividad() { setActividades(prev => [...prev, { torre: '', horas: 43, personas: 1 }]) }

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const result = await generarCronograma({ proyecto, cliente, roles, actividades })
      download(
        result.content_b64,
        result.filename,
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      )
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="cronograma-form" onSubmit={handleSubmit}>
      <h2>Generar Cronograma</h2>

      <label>Proyecto
        <input value={proyecto} onChange={e => setProyecto(e.target.value)} />
      </label>
      <label>Cliente
        <input value={cliente} onChange={e => setCliente(e.target.value)} />
      </label>

      <section>
        <h3>Roles</h3>
        {roles.map((r, i) => (
          <div key={i} className="row-inline">
            <input placeholder="Perfil / Rol" value={r.perfil}
              onChange={e => setRoles(prev => prev.map((x, j) => j === i ? {...x, perfil: e.target.value} : x))} />
            <input placeholder="Seniority" value={r.seniority}
              onChange={e => setRoles(prev => prev.map((x, j) => j === i ? {...x, seniority: e.target.value} : x))} />
            <input type="number" placeholder="Personas" value={r.personas} min={1}
              onChange={e => setRoles(prev => prev.map((x, j) => j === i ? {...x, personas: +e.target.value} : x))} />
            <input placeholder="Torre" value={r.torre}
              onChange={e => setRoles(prev => prev.map((x, j) => j === i ? {...x, torre: e.target.value} : x))} />
          </div>
        ))}
        <button type="button" onClick={addRol} className="btn-secondary">+ Rol</button>
      </section>

      <section>
        <h3>Actividades</h3>
        {actividades.map((a, i) => (
          <div key={i} className="row-inline">
            <input placeholder="Torre / Actividad" value={a.torre}
              onChange={e => setActividades(prev => prev.map((x, j) => j === i ? {...x, torre: e.target.value} : x))} />
            <input type="number" placeholder="Horas" value={a.horas} min={1}
              onChange={e => setActividades(prev => prev.map((x, j) => j === i ? {...x, horas: +e.target.value} : x))} />
            <input type="number" placeholder="Personas" value={a.personas} min={1}
              onChange={e => setActividades(prev => prev.map((x, j) => j === i ? {...x, personas: +e.target.value} : x))} />
          </div>
        ))}
        <button type="button" onClick={addActividad} className="btn-secondary">+ Actividad</button>
      </section>

      {error && <p className="error-text">{error}</p>}
      <button className="btn-primary" type="submit" disabled={loading}>
        {loading ? 'Generando...' : 'Descargar Cronograma .xlsx'}
      </button>
    </form>
  )
}
