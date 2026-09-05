import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { getCameraMeta, removeCameraMeta, setCameraMeta, withMeta } from '../utils/hospitalMeta'

function CameraEditor({ camera, onClose, onSaved }) {
  const meta = getCameraMeta(camera)
  const [form, setForm] = useState({
    name: camera.name, source: camera.source, room: camera.room || '', enabled: camera.enabled,
    check_mask: camera.check_mask, check_hat: camera.check_hat, check_wash: camera.check_wash,
    department: meta.department, floor: meta.floor, type: meta.type, purpose: meta.purpose,
  })
  const [saving, setSaving] = useState(false)
  const save = async e => {
    e.preventDefault(); setSaving(true)
    await api.cameras.update(camera.id, {
      name: form.name, source: form.source, room: form.room, enabled: form.enabled,
      check_mask: form.check_mask, check_hat: form.check_hat, check_wash: form.check_wash,
    })
    setCameraMeta(camera.id, { department: form.department, floor: form.floor, type: form.type, purpose: form.purpose })
    setSaving(false); onSaved(); onClose()
  }
  return <div className="modal-backdrop"><form className="modal card" onSubmit={save}>
    <div className="modal-head"><div><span className="eyebrow">CAMERA CONFIGURATION</span><h2>Edit {camera.name}</h2></div><button type="button" className="icon-button" onClick={onClose}>×</button></div>
    <div className="form-grid">
      <label className="field"><span>Camera Name</span><input value={form.name} onChange={e => setForm({...form,name:e.target.value})} required /></label>
      <label className="field"><span>Camera Type</span><select value={form.type} onChange={e => setForm({...form,type:e.target.value})}><option>Webcam</option><option>Dahua / IP Camera</option><option>Other IP Camera</option></select></label>
      <label className="field"><span>Department</span><input value={form.department} onChange={e => setForm({...form,department:e.target.value})} placeholder="Surgery" /></label>
      <label className="field"><span>Room</span><input value={form.room} onChange={e => setForm({...form,room:e.target.value})} placeholder="Operating Theater 01" /></label>
      <label className="field"><span>Floor / Area</span><input value={form.floor} onChange={e => setForm({...form,floor:e.target.value})} placeholder="Level 2" /></label>
      <label className="field"><span>Purpose / Location</span><input value={form.purpose} onChange={e => setForm({...form,purpose:e.target.value})} placeholder="Sink Monitoring Camera" /></label>
      <label className="field full"><span>Source</span><input value={form.source} onChange={e => setForm({...form,source:e.target.value})} required /></label>
    </div>
    <div className="check-grid">
      {[['enabled','Camera enabled'],['check_mask','Mask detection'],['check_hat','Hat detection'],['check_wash','Hand-wash detection']].map(([k,l]) => <label className="switch-row" key={k}><span>{l}</span><input type="checkbox" checked={form[k]} onChange={e => setForm({...form,[k]:e.target.checked})} /></label>)}
    </div>
    <div className="modal-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={saving}>{saving?'Saving…':'Save camera'}</button></div>
  </form></div>
}

function AddCamera({ onCreated }) {
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ name:'', type:'Webcam', department:'Unassigned', room:'', floor:'Unassigned', purpose:'Sink Monitoring Camera', source:'', enabled:true, check_mask:true, check_hat:true, check_wash:true })
  const create = async e => {
    e.preventDefault()
    const c = await api.cameras.create({ name:form.name, source:form.source, room:form.room, enabled:form.enabled, check_mask:form.check_mask, check_hat:form.check_hat, check_wash:form.check_wash })
    setCameraMeta(c.id, { department:form.department, floor:form.floor, type:form.type, purpose:form.purpose })
    setOpen(false); onCreated()
  }
  return <>
    <button className="btn btn-primary" onClick={() => setOpen(true)}>+ Add Camera</button>
    {open && <div className="modal-backdrop"><form className="modal card" onSubmit={create}>
      <div className="modal-head"><div><span className="eyebrow">NEW CAMERA</span><h2>Add Camera</h2></div><button type="button" className="icon-button" onClick={() => setOpen(false)}>×</button></div>
      <div className="form-grid">
        <label className="field"><span>Camera Name</span><input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required /></label>
        <label className="field"><span>Camera Type</span><select value={form.type} onChange={e=>setForm({...form,type:e.target.value})}><option>Webcam</option><option>Dahua / IP Camera</option><option>Other IP Camera</option></select></label>
        <label className="field"><span>Department</span><input value={form.department} onChange={e=>setForm({...form,department:e.target.value})} /></label>
        <label className="field"><span>Room</span><input value={form.room} onChange={e=>setForm({...form,room:e.target.value})} required /></label>
        <label className="field"><span>Floor / Area</span><input value={form.floor} onChange={e=>setForm({...form,floor:e.target.value})} /></label>
        <label className="field"><span>Purpose</span><input value={form.purpose} onChange={e=>setForm({...form,purpose:e.target.value})} /></label>
        <label className="field full"><span>Source</span><input value={form.source} onChange={e=>setForm({...form,source:e.target.value})} placeholder="0 or rtsp://..." required /></label>
      </div>
      <div className="check-grid">{[['enabled','Camera enabled'],['check_mask','Mask detection'],['check_hat','Hat detection'],['check_wash','Hand-wash detection']].map(([k,l]) => <label className="switch-row" key={k}><span>{l}</span><input type="checkbox" checked={form[k]} onChange={e=>setForm({...form,[k]:e.target.checked})}/></label>)}</div>
      <div className="modal-actions"><button type="button" className="btn" onClick={()=>setOpen(false)}>Cancel</button><button className="btn btn-primary">Add Camera</button></div>
    </form></div>}
  </>
}

export default function Cameras() {
  const [cameras, setCameras] = useState([])
  const [statuses, setStatuses] = useState({})
  const [editing, setEditing] = useState(null)
  const [search, setSearch] = useState('')
  const load = async () => {
    const cams = (await api.cameras.list()).map(withMeta); setCameras(cams)
    const pairs = await Promise.all(cams.map(async c => { try { return [c.id, await api.cameras.status(c.id)] } catch { return [c.id, null] } }))
    setStatuses(Object.fromEntries(pairs))
  }
  useEffect(() => { load(); const t=setInterval(load,7000); return()=>clearInterval(t) }, [])
  const filtered = useMemo(() => cameras.filter(c => `${c.name} ${c.room} ${c.meta.department} ${c.meta.purpose}`.toLowerCase().includes(search.toLowerCase())), [cameras, search])
  const remove = async c => { if (!confirm(`Delete camera "${c.name}"?`)) return; await api.cameras.remove(c.id); removeCameraMeta(c.id); load() }
  const toggle = async c => { await api.cameras.update(c.id,{enabled:!c.enabled}); load() }
  const test = async c => { try { const s=await api.cameras.status(c.id); alert(s.connected ? `${c.name}: connection is healthy.` : `${c.name}: backend reports camera offline.`) } catch { alert(`${c.name}: connection test failed.`) } }
  return <div>
    <div className="page-header"><div><span className="eyebrow">HOSPITAL / CAMERAS</span><h1 className="page-title">Cameras</h1><div className="page-subtitle">Department → Room → Camera configuration and health</div></div><AddCamera onCreated={load}/></div>
    <div className="filter-bar"><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search cameras, rooms, departments…" /></div>
    <div className="table-shell"><table className="data-table camera-table"><thead><tr><th>Camera</th><th>Department / Room</th><th>Type</th><th>Source</th><th>State</th><th>AI Checks</th><th>Actions</th></tr></thead><tbody>
      {filtered.map(c => <tr key={c.id}>
        <td><button className="table-link" onClick={()=>window.open(`/cameras/${c.id}`,'_blank')}>{c.name} ↗</button><small>{c.meta.purpose}</small></td>
        <td><strong>{c.meta.department}</strong><small>{c.room || 'Unassigned room'} · {c.meta.floor}</small></td>
        <td>{c.meta.type}</td><td className="mono source-cell">{c.source}</td>
        <td><span className={'pill '+(statuses[c.id]?.connected?'pill-ok':'pill-neutral')}>{statuses[c.id]?.connected?'ONLINE':'OFFLINE'}</span><small>{c.enabled?'Enabled':'Disabled'}</small></td>
        <td><div className="check-pills"><span className={'mini-check '+(c.check_mask?'on':'')}>MASK</span><span className={'mini-check '+(c.check_hat?'on':'')}>HAT</span><span className={'mini-check '+(c.check_wash?'on':'')}>WASH</span></div></td>
        <td><div className="row-actions"><button className="btn btn-sm" onClick={()=>setEditing(c)}>Edit</button><button className="btn btn-sm" onClick={()=>test(c)}>Test</button><button className="btn btn-sm" onClick={()=>toggle(c)}>{c.enabled?'Disable':'Enable'}</button><button className="btn btn-sm btn-danger" onClick={()=>remove(c)}>Delete</button></div></td>
      </tr>)}
    </tbody></table></div>
    {!filtered.length && <div className="empty-state">No cameras found.</div>}
    {editing && <CameraEditor camera={editing} onClose={()=>setEditing(null)} onSaved={load}/>} 
  </div>
}
