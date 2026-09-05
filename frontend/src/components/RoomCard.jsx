import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

export default function RoomCard({ room }) {
  const [statuses, setStatuses] = useState({})
  useEffect(() => {
    let alive = true
    const load = async () => {
      const pairs = await Promise.all(room.cameras.map(async c => {
        try { return [c.id, await api.cameras.status(c.id)] } catch { return [c.id, null] }
      }))
      if (alive) setStatuses(Object.fromEntries(pairs))
    }
    load(); const t = setInterval(load, 3000); return () => { alive = false; clearInterval(t) }
  }, [room.key])

  const stats = useMemo(() => {
    const vals = Object.values(statuses)
    return {
      online: vals.filter(s => s?.connected).length,
      active: vals.filter(s => s?.is_auth).length,
      compliant: vals.some(s => s?.master_ready),
      attention: vals.some(s => s?.is_auth && !s?.master_ready),
    }
  }, [statuses])

  const openRoom = () => window.open(`/rooms/${room.slug}`, '_blank', 'noopener,noreferrer')

  return (
    <article className="room-card" onClick={openRoom} role="button" tabIndex={0} onKeyDown={e => e.key === 'Enter' && openRoom()}>
      <div className="room-card-top">
        <div><span className="eyebrow">{room.department}</span><h3>{room.name}</h3><p>{room.floor !== 'Unassigned' ? room.floor : 'Hospital monitoring area'}</p></div>
        <span className={'room-state ' + (stats.attention ? 'attention' : 'normal')}>{stats.attention ? 'Attention' : '✓ Normal'}</span>
      </div>
      <div className="room-metrics">
        <div><strong>{room.cameras.length}</strong><span>Cameras</span></div>
        <div><strong>{stats.online}</strong><span>Online</span></div>
        <div><strong>{room.cameras.length - stats.online}</strong><span>Offline</span></div>
        <div><strong>{stats.active}</strong><span>Active</span></div>
      </div>
      <div className="room-previews">
        {room.cameras.slice(0, 3).map(c => (
          <div className="room-preview" key={c.id}>
            {c.enabled ? <img src={api.streamUrl(c.id)} alt={c.name} /> : <span>NO SIGNAL</span>}
            <small>{c.name}</small>
          </div>
        ))}
        {room.cameras.length > 3 && <div className="room-preview-more">+{room.cameras.length - 3}</div>}
      </div>
      <div className="room-card-foot"><span>Open monitoring workspace</span><strong>↗</strong></div>
    </article>
  )
}
