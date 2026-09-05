import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { withMeta } from '../utils/hospitalMeta'

function userName(s){return s?.user && s.user !== 'EMPTY' ? s.user : 'No active user'}
export default function LiveCameras(){
  const [cameras,setCameras]=useState([]),[statuses,setStatuses]=useState({}),[search,setSearch]=useState('')
  const load=async()=>{try{const cams=(await api.cameras.list()).map(withMeta);setCameras(cams);const pairs=await Promise.all(cams.map(async c=>{try{return[c.id,await api.cameras.status(c.id)]}catch{return[c.id,null]}}));setStatuses(Object.fromEntries(pairs))}catch{}}
  useEffect(()=>{load();const t=setInterval(load,4000);return()=>clearInterval(t)},[])
  const online=useMemo(()=>cameras.filter(c=>statuses[c.id]?.connected&&`${c.name} ${c.room} ${c.meta.department}`.toLowerCase().includes(search.toLowerCase())),[cameras,statuses,search])
  return <div><div className="page-header"><div><span className="eyebrow">LIVE OPERATIONS / ALL ROOMS</span><h1 className="page-title">Live Cameras</h1><div className="page-subtitle">All cameras currently online, independent of department or room</div></div><div className="live-indicator"><span className="status-dot online"/>{online.length} ONLINE</div></div>
    <div className="filter-bar compact-filter"><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search camera, room or department…"/></div>
    <div className="live-wall">{online.map(c=>{const s=statuses[c.id];return <article className="live-tile" key={c.id} onClick={()=>window.open(`/cameras/${c.id}`,'_blank','noopener,noreferrer')}><div className="live-tile-video"><img src={api.streamUrl(c.id)} alt={c.name}/><span className="live-badge"><i/>LIVE</span><span className="tile-room">{c.room||'Unassigned room'}</span></div><div className="live-tile-body"><div className="tile-title"><div><strong>{c.name}</strong><small>{c.meta.department} · {c.meta.purpose}</small></div><span className={'auth-state '+(s?.is_auth?'active':'idle')}>{s?.is_auth?'AUTH':'IDLE'}</span></div><div className="tile-user"><span>CURRENT USER</span><strong>{s?.is_auth?userName(s):'No active user'}</strong></div><div className="tile-status-row"><span>Mask <b className={s?.mask?'ok-text':''}>{s?.is_auth?(s?.mask?'PASS':'—'):'—'}</b></span><span>Hat <b className={s?.hat?'ok-text':''}>{s?.is_auth?(s?.hat?'PASS':'—'):'—'}</b></span><span>Wash <b>{s?.wash_time!=null?`${Math.round(s.wash_time)}s`:'—'}</b></span></div></div></article>})}</div>
    {!online.length&&<div className="empty-state">No online cameras match this view.</div>}
  </div>
}
