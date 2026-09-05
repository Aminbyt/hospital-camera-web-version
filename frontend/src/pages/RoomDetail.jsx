import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'
import CameraCard from '../components/CameraCard'
import Breadcrumbs from '../components/Breadcrumbs'
import { decodeRoomSlug, withMeta } from '../utils/hospitalMeta'

export default function RoomDetail() {
  const { slug } = useParams()
  const target = decodeRoomSlug(slug)
  const [cameras, setCameras] = useState([])
  const [statuses, setStatuses] = useState({})
  const [filter, setFilter] = useState('all')

  const load = async () => {
    const all = (await api.cameras.list()).map(withMeta)
    const cams = all.filter(c => (c.room || 'Unassigned Room') === target.name && c.meta.department === target.department)
    setCameras(cams)
    const pairs = await Promise.all(cams.map(async c => { try { return [c.id, await api.cameras.status(c.id)] } catch { return [c.id, null] } }))
    setStatuses(Object.fromEntries(pairs))
  }
  useEffect(() => { load(); const t = setInterval(load, 3000); return () => clearInterval(t) }, [slug])

  const vals = Object.values(statuses)
  const filtered = useMemo(() => cameras.filter(c => {
    const s = statuses[c.id]
    if (filter === 'online') return s?.connected
    if (filter === 'offline') return !s?.connected
    if (filter === 'attention') return s?.connected && s?.is_auth && !s?.master_ready
    return true
  }), [cameras, statuses, filter])

  return <div>
    <Breadcrumbs items={[{ label: target.department, to: '/rooms' }, { label: target.name }]} />
    <div className="page-header room-detail-header"><div><span className="eyebrow">{target.department} DEPARTMENT</span><h1 className="page-title">{target.name}</h1><div className="page-subtitle">Dedicated room monitoring workspace</div></div>
      <div className="summary-strip"><div><strong>{cameras.length}</strong><span>Cameras</span></div><div><strong>{vals.filter(s => s?.connected).length}</strong><span>Online</span></div><div><strong>{cameras.length - vals.filter(s => s?.connected).length}</strong><span>Offline</span></div><div><strong>{vals.filter(s => s?.is_auth).length}</strong><span>Active Users</span></div></div>
    </div>
    <div className="segmented-control">{[['all','All Cameras'],['online','Online'],['offline','Offline'],['attention','Attention Required']].map(([v,l]) => <button className={filter === v ? 'active' : ''} key={v} onClick={() => setFilter(v)}>{l}</button>)}</div>
    <div className="camera-grid room-camera-grid">{filtered.map(c => <CameraCard key={c.id} camera={c} initialStatus={statuses[c.id]} />)}</div>
    {!filtered.length && <div className="empty-state">No cameras in this view.</div>}
  </div>
}
