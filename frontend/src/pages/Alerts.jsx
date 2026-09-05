import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { withMeta } from '../utils/hospitalMeta'

function severityOf(a){
  const l=(a.level||'info').toLowerCase(); const m=(a.message||'').toLowerCase()
  if(l==='critical'||m.includes('offline')||m.includes('connection lost')) return 'critical'
  if(l==='warning'||m.includes('missing')||m.includes('incomplete')||m.includes('non-compliant')) return 'attention'
  return 'info'
}
export default function Alerts(){
  const [alerts,setAlerts]=useState([]),[cameras,setCameras]=useState([]),[loading,setLoading]=useState(true)
  useEffect(()=>{const load=async()=>{const [a,c]=await Promise.all([api.alerts.list(),api.cameras.list()]);setAlerts(a);setCameras(c.map(withMeta));setLoading(false)};load();const t=setInterval(load,5000);return()=>clearInterval(t)},[])
  const groups=useMemo(()=>({critical:alerts.filter(a=>severityOf(a)==='critical'),attention:alerts.filter(a=>severityOf(a)==='attention'),info:alerts.filter(a=>severityOf(a)==='info')}),[alerts])
  const camMap=Object.fromEntries(cameras.map(c=>[c.name,c]))
  const render=(title,key)=> <section className="alert-group"><div className="alert-group-title"><span className={`severity-marker ${key}`}/><h2>{title}</h2><span>{groups[key].length}</span></div>{groups[key].map(a=>{const c=camMap[a.camera_name];return <article className={`alert-row ${key}`} key={a.id}><div className="alert-main"><span className={`severity-label ${key}`}>{title.toUpperCase()}</span><div><strong>{c?.room||'Hospital System'}</strong><span>{a.camera_name||'System'}</span></div><p>{a.message}</p></div><div className="alert-meta"><span className={'pill '+(a.delivered?'pill-ok':'pill-neutral')}>{a.delivered?'DELIVERED':'LOGGED ONLY'}</span><small className="mono">Alert #{a.id}</small></div></article>})}{!groups[key].length&&<div className="quiet-row">No {title.toLowerCase()} alerts.</div>}</section>
  return <div><div className="page-header"><div><span className="eyebrow">OPERATIONS / ALERTS</span><h1 className="page-title">Alert Management</h1><div className="page-subtitle">Clinical and camera conditions requiring operator awareness</div></div></div>{loading?<div className="empty-state">Loading alerts…</div>:<div className="alerts-layout">{render('Critical','critical')}{render('Attention','attention')}{render('Informational','info')}</div>}</div>
}
