import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Events() {
  const [events, setEvents] = useState([])
  const [cameras, setCameras] = useState([])
  const [filters, setFilters] = useState({ camera_id: '', date_from: '', date_to: '', user: '' })
  const [loading, setLoading] = useState(true)

  useEffect(() => { api.cameras.list().then(setCameras) }, [])

  const load = () => {
    setLoading(true)
    const params = {}
    Object.entries(filters).forEach(([k, v]) => { if (v) params[k] = v })
    api.events.list(params).then(setEvents).finally(() => setLoading(false))
  }

  useEffect(load, [])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Events / History</h1>
          <div className="page-subtitle">Every logged visit — filter, review, export</div>
        </div>
        <a className="btn btn-primary" href={api.events.exportUrl(
          Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
        )}>Export to Excel</a>
      </div>

      <div className="toolbar">
        <select className="field" style={{ marginBottom: 0 }} value={filters.camera_id}
          onChange={(e) => setFilters({ ...filters, camera_id: e.target.value })}>
          <option value="">All cameras</option>
          {cameras.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input placeholder="From (YYYY-MM-DD)" value={filters.date_from}
          onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
        <input placeholder="To (YYYY-MM-DD)" value={filters.date_to}
          onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
        <input placeholder="Search staff name…" value={filters.user}
          onChange={(e) => setFilters({ ...filters, user: e.target.value })} />
        <button className="btn" onClick={load}>Apply filters</button>
      </div>

      {loading && <p className="muted">Loading…</p>}
      {!loading && events.length === 0 && <div className="empty-state">No events match these filters.</div>}

      {!loading && events.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th><th>Time</th><th>Sink</th><th>Staff</th><th>Role</th>
              <th>Mask</th><th>Hat</th><th>Wash</th><th>Duration</th><th>WHO Steps</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id}>
                <td className="mono">{e.date}</td>
                <td className="mono">{e.time}</td>
                <td>{e.camera_name}</td>
                <td>{e.first_name} {e.last_name}</td>
                <td>{e.role}</td>
                <td>{e.mask === 'YES' ? '✓' : '✕'}</td>
                <td>{e.hat === 'YES' ? '✓' : '✕'}</td>
                <td>{e.washing_complete === 'YES' ? '✓' : '✕'}</td>
                <td className="mono">{e.wash_duration}s</td>
                <td>{e.all_who_steps === 'YES' ? '✓' : '✕'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
