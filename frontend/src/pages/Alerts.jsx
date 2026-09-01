import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = () => api.alerts.list().then(setAlerts).finally(() => setLoading(false))
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Alerts</h1>
          <div className="page-subtitle">Every bot notification sent on staff logout</div>
        </div>
      </div>

      {loading && <p className="muted">Loading…</p>}
      {!loading && alerts.length === 0 && (
        <div className="empty-state">No alerts yet. They appear here whenever a staff member logs out of a sink.</div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {alerts.map((a) => (
          <div key={a.id} className="card" style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13.5 }}>{a.camera_name || 'System'}</div>
              <pre style={{
                margin: '6px 0 0', fontFamily: 'var(--font-mono)', fontSize: 12,
                whiteSpace: 'pre-wrap', color: 'var(--ink-muted)',
              }}>{a.message}</pre>
            </div>
            <span className={'pill ' + (a.delivered ? 'pill-ok' : 'pill-neutral')} style={{ height: 'fit-content' }}>
              {a.delivered ? 'DELIVERED' : 'LOGGED ONLY'}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
