import { Link } from 'react-router-dom'

export default function Breadcrumbs({ items = [] }) {
  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <Link to="/">Hospital</Link>
      {items.map((item, i) => (
        <span key={`${item.label}-${i}`} className="breadcrumb-part">
          <span>/</span>
          {item.to ? <Link to={item.to}>{item.label}</Link> : <strong>{item.label}</strong>}
        </span>
      ))}
    </nav>
  )
}
