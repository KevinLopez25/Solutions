export default function CatalogoTable({ title, items, columns, onDelete, onEdit }) {
  if (!items?.length) return <p className="empty-state">Sin registros en {title}</p>

  return (
    <div className="catalogo-table-wrapper">
      <h3>{title}</h3>
      <table className="catalogo-table">
        <thead>
          <tr>
            {columns.map(c => <th key={c.key}>{c.label}</th>)}
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={item.id}>
              {columns.map(c => <td key={c.key}>{item[c.key]}</td>)}
              <td>
                {onEdit  && <button className="btn-icon" onClick={() => onEdit(item)}>✎</button>}
                {onDelete && <button className="btn-icon danger" onClick={() => onDelete(item.id)}>✕</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
