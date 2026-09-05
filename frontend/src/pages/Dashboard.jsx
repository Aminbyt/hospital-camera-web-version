import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import RoomCard from '../components/RoomCard'
import { groupRooms, withMeta } from '../utils/hospitalMeta'
import { weekLabel, weekRange } from '../utils/week'

function compliant(e){return e.mask==='YES'&&e.hat==='YES'&&e.washing_complete==='YES'&&e.all_who_steps==='YES'}
function KPI({label,value,tone='',hint}){return <div className={'kpi-card '+tone}><span>{label}</span><strong>{value}</strong>{hint&&<small>{hint}</small>}</div>}
function dayName(date){return new Date(`${date}T12:00:00`).toLocaleDateString(undefined,{weekday:'short'})}

function WeeklyActivity({ events, range }) {
  const days = useMemo(() => {
    const rows=[]
    for(let i=0;i<7;i++){
      const d=new Date(range.start);d.setDate(d.getDate()+i)
      const key=`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`
      const all=events.filter(e=>e.date===key), ok=all.filter(compliant).length
      rows.push({key,label:dayName(key),total:all.length,ok})
    }
    return rows
  },[events,range.date_from])
  const max=Math.max(1,...days.map(d=>d.total))
  return <div className="analytics-card">
    <div className="analytics-head"><div><span className="eyebrow">WEEKLY ACTIVITY</span><h3>Hand-wash detections</h3></div><strong>{events.length} sessions</strong></div>
    <div className="weekly-bars">{days.map(d=><div className="day-bar" key={d.key}><div className="bar-value">{d.total}</div><div className="bar-track"><div className="bar-fill" style={{height:`${Math.max(4,d.total/max*100)}%`}}><div className="bar-compliant" style={{height:`${d.total?d.ok/d.total*100:0}%`}} /></div></div><span>{d.label}</span></div>)}</div>
    <div className="chart-legend"><span><i className="legend-total"/>Total detections</span><span><i className="legend-ok"/>Compliant</span></div>
  </div>
}

function TopEmployees({events}){
  const staff=useMemo(()=>{const map=new Map();events.forEach(e=>{const name=`${e.first_name||''} ${e.last_name||''}`.trim()||'Unknown';const v=map.get(name)||{name,role:e.role||'Staff',visits:0,compliant:0};v.visits++;if(compliant(e))v.compliant++;map.set(name,v)});return [...map.values()].sort((a,b)=>b.visits-a.visits).slice(0,6)},[events])
  const max=Math.max(1,...staff.map(s=>s.visits))
  return <div className="analytics-card"><div className="analytics-head"><div><span className="eyebrow">EMPLOYEE ACTIVITY</span><h3>Most detected staff</h3></div><small>by sessions this week</small></div>
    <div className="ranking-list">{staff.length?staff.map((s,i)=><div className="rank-row" key={s.name}><span className="rank-no">{String(i+1).padStart(2,'0')}</span><div className="rank-person"><strong>{s.name}</strong><small>{s.role}</small><div className="rank-track"><span style={{width:`${s.visits/max*100}%`}}/></div></div><div className="rank-stat"><strong>{s.visits}</strong><small>{Math.round(s.compliant/s.visits*100)}% compliant</small></div></div>):<div className="quiet-row">No employee sessions in this week.</div>}</div>
  </div>
}

function RoomActivity({events,cameras}){
  const byName=Object.fromEntries(cameras.map(c=>[c.name,c]));
  const rows=useMemo(()=>{const m=new Map();events.forEach(e=>{const c=byName[e.camera_name];const room=c?.room||'Unknown room';m.set(room,(m.get(room)||0)+1)});return [...m.entries()].sort((a,b)=>b[1]-a[1]).slice(0,6)},[events,cameras])
  const max=Math.max(1,...rows.map(r=>r[1]));
  return <div className="analytics-card"><div className="analytics-head"><div><span className="eyebrow">ROOM UTILIZATION</span><h3>Sessions by room</h3></div></div><div className="room-activity-list">{rows.length?rows.map(([room,count])=><div className="room-activity-row" key={room}><div><strong>{room}</strong><small>{count} detected sessions</small></div><div className="horizontal-meter"><span style={{width:`${count/max*100}%`}}/></div><b>{count}</b></div>):<div className="quiet-row">No room activity in this week.</div>}</div></div>
}

export default function Dashboard(){
  const [cameras,setCameras]=useState([]),[statuses,setStatuses]=useState({}),[events,setEvents]=useState([]),[alerts,setAlerts]=useState([]),[loading,setLoading]=useState(true),[weekOffset,setWeekOffset]=useState(0)
  const range=useMemo(()=>weekRange(weekOffset),[weekOffset])
  const loadLive=async()=>{try{const cams=(await api.cameras.list()).map(withMeta);setCameras(cams);const pairs=await Promise.all(cams.map(async c=>{try{return[c.id,await api.cameras.status(c.id)]}catch{return[c.id,null]}}));setStatuses(Object.fromEntries(pairs));setAlerts(await api.alerts.list())}catch{}finally{setLoading(false)}}
  const loadWeek=async()=>{try{setEvents(await api.events.list({date_from:range.date_from,date_to:range.date_to}))}catch{setEvents([])}}
  useEffect(()=>{loadLive();const t=setInterval(loadLive,8000);return()=>clearInterval(t)},[])
  useEffect(()=>{loadWeek()},[range.date_from,range.date_to])
  const rooms=useMemo(()=>groupRooms(cameras),[cameras]);const statusVals=Object.values(statuses);const ok=events.filter(compliant).length;const activeAlerts=alerts.filter(a=>!a.delivered||a.level==='critical'||a.level==='warning').length
  return <div>
    <div className="page-header command-header"><div><span className="eyebrow">HOSPITAL OPERATIONS / WEEKLY COMMAND VIEW</span><h1 className="page-title">Command Dashboard</h1><div className="page-subtitle">Clinical operations, employee activity and AI hand-hygiene performance</div></div><div className="dashboard-period"><label>Reporting week</label><select value={weekOffset} onChange={e=>setWeekOffset(Number(e.target.value))}><option value={0}>Current week · {weekLabel(0)}</option><option value={1}>1 week ago · {weekLabel(1)}</option><option value={2}>2 weeks ago · {weekLabel(2)}</option><option value={3}>3 weeks ago · {weekLabel(3)}</option></select></div></div>
    <div className="reporting-banner"><div><span>REPORTING WINDOW</span><strong>{weekLabel(weekOffset)}</strong></div><p>Dashboard analytics are calculated from this selected Monday–Sunday period. Live camera health remains current.</p><div className="live-indicator"><span className="status-dot online"/>LIVE CAMERA STATUS</div></div>
    <div className="kpi-grid dashboard-kpis"><KPI label="Total Rooms" value={rooms.length}/><KPI label="Total Cameras" value={cameras.length}/><KPI label="Cameras Online" value={statusVals.filter(s=>s?.connected).length} tone="good" hint="live now"/><KPI label="Cameras Offline" value={cameras.length-statusVals.filter(s=>s?.connected).length} tone="neutral" hint="live now"/><KPI label="Active Alerts" value={activeAlerts} tone={activeAlerts?'warn':''} hint="live now"/><KPI label="Active Sessions" value={statusVals.filter(s=>s?.is_auth).length} hint="live now"/><KPI label="Compliant Sessions" value={ok} tone="good" hint="selected week"/><KPI label="Non-Compliant" value={Math.max(0,events.length-ok)} tone={events.length-ok?'warn':''} hint="selected week"/></div>
    <section className="section-block"><div className="section-heading"><div><span className="eyebrow">ROOM OVERVIEW</span><h2>Clinical Areas</h2></div><a href="/rooms">View all rooms →</a></div>{loading&&<div className="empty-state">Loading hospital status…</div>}<div className="room-grid">{rooms.map(room=><RoomCard key={room.key} room={room}/>)}</div>{!loading&&!rooms.length&&<div className="empty-state">No rooms are assigned yet. Define rooms in Settings, then assign cameras to them.</div>}</section>
    <section className="section-block"><div className="section-heading"><div><span className="eyebrow">WEEKLY OPERATIONS INTELLIGENCE</span><h2>People & Hand Hygiene</h2></div><span className="section-period">{weekLabel(weekOffset)}</span></div><div className="analytics-grid"><WeeklyActivity events={events} range={range}/><TopEmployees events={events}/><RoomActivity events={events} cameras={cameras}/></div></section>
  </div>
}
