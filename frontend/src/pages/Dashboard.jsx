import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import RoomCard from '../components/RoomCard'
import { groupRooms, withMeta } from '../utils/hospitalMeta'

function KPI({ label, value, tone = '' }) {
  return <div className={'kpi-card ' + tone}><span>{label}</span><strong>{value}</strong></div>
}

export default function Dashboard() {
  const [cameras, setCameras] = useState([])
  const [statuses, setStatuses] = useState({})
  const [events, setEvents] = useState([])
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const cams = (await api.cameras.list()).map(withMeta)
      setCameras(cams)
      const statusPairs = await Promise.all(cams.map(async c => { try { return [c.id, await api.cameras.status(c.id)] } catch { return [c.id, null] } }))
      setStatuses(Object.fromEntries(statusPairs))
      const today = new Date().toISOString().slice(0, 10)
      const [ev, al] = await Promise.all([api.events.list({ date_from: today, date_to: today }), api.alerts.list()])
      setEvents(ev); setAlerts(al)
    } finally { setLoading(false) }
  }
  useEffect(() => { load(); const t = setInterval(load, 8000); return () => clearInterval(t) }, [])

  const rooms = useMemo(() => groupRooms(cameras), [cameras])
  const statusVals = Object.values(statuses)
  const compliant = events.filter(e => e.mask === 'YES' && e.hat === 'YES' && e.washing_complete === 'YES' && e.all_who_steps === 'YES').length
  const activeAlerts = alerts.filter(a => !a.delivered || a.level === 'critical' || a.level === 'warning').length

  return <div>
    <div className="page-header command-header">
      <div><span className="eyebrow">HOSPITAL OPERATIONS</span><h1 className="page-title">Command Dashboard</h1><div className="page-subtitle">Hospital-wide hand hygiene and AI camera monitoring</div></div>
      <div className="live-indicator"><span className="status-dot online" /> LIVE OPERATIONS</div>
    </div>

    <div className="kpi-grid">
      <KPI label="Total Rooms" value={rooms.length} />
      <KPI label="Total Cameras" value={cameras.length} />
      <KPI label="Cameras Online" value={statusVals.filter(s => s?.connected).length} tone="good" />
      <KPI label="Cameras Offline" value={cameras.length - statusVals.filter(s => s?.connected).length} tone="neutral" />
      <KPI label="Active Alerts" value={activeAlerts} tone={activeAlerts ? 'warn' : ''} />
      <KPI label="Active Sessions" value={statusVals.filter(s => s?.is_auth).length} />
      <KPI label="Compliant Today" value={compliant} tone="good" />
      <KPI label="Non-Compliant Today" value={Math.max(0, events.length - compliant)} tone={events.length - compliant ? 'warn' : ''} />
    </div>

    <section className="section-block">
      <div className="section-heading"><div><span className="eyebrow">ROOM OVERVIEW</span><h2>Clinical Areas</h2></div><a href="/rooms">View all rooms →</a></div>
      {loading && <div className="empty-state">Loading hospital status…</div>}
      {!loading && rooms.length === 0 && <div className="empty-state">No rooms yet. Assign a room to a camera from Cameras or Settings.</div>}
      <div className="room-grid">{rooms.map(room => <RoomCard key={room.key} room={room} />)}</div>
    </section>
  </div>
}
