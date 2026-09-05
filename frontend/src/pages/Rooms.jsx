import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import RoomCard from '../components/RoomCard'
import { groupRooms, withMeta } from '../utils/hospitalMeta'

export default function Rooms() {
  const [cameras, setCameras] = useState([])
  const [search, setSearch] = useState('')
  const [department, setDepartment] = useState('')
  const [floor, setFloor] = useState('')
  const [sort, setSort] = useState('name')

  const load = () => api.cameras.list().then(c => setCameras(c.map(withMeta)))
  useEffect(() => { load(); window.addEventListener('akam-meta-updated', load); return () => window.removeEventListener('akam-meta-updated', load) }, [])

  const rooms = useMemo(() => groupRooms(cameras), [cameras])
  const departments = [...new Set(rooms.map(r => r.department))].sort()
  const floors = [...new Set(rooms.map(r => r.floor))].sort()
  const filtered = rooms.filter(r => (!search || `${r.name} ${r.department}`.toLowerCase().includes(search.toLowerCase())) && (!department || r.department === department) && (!floor || r.floor === floor))
    .sort((a, b) => sort === 'department' ? a.department.localeCompare(b.department) : sort === 'cameras' ? b.cameras.length - a.cameras.length : a.name.localeCompare(b.name))

  const grouped = Object.groupBy ? Object.groupBy(filtered, r => r.department) : filtered.reduce((acc, r) => ((acc[r.department] ||= []).push(r), acc), {})

  return <div>
    <div className="page-header"><div><span className="eyebrow">HOSPITAL / ROOMS</span><h1 className="page-title">Rooms</h1><div className="page-subtitle">Monitor clinical areas by department and room</div></div></div>
    <div className="filter-bar">
      <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search rooms…" />
      <select value={department} onChange={e => setDepartment(e.target.value)}><option value="">All departments</option>{departments.map(d => <option key={d}>{d}</option>)}</select>
      <select value={floor} onChange={e => setFloor(e.target.value)}><option value="">All floors / areas</option>{floors.map(f => <option key={f}>{f}</option>)}</select>
      <select value={sort} onChange={e => setSort(e.target.value)}><option value="name">Sort: Room name</option><option value="department">Sort: Department</option><option value="cameras">Sort: Camera count</option></select>
    </div>
    {Object.entries(grouped).map(([dept, deptRooms]) => <section className="department-section" key={dept}>
      <div className="department-title"><span>{dept}</span><small>{deptRooms.length} room{deptRooms.length !== 1 ? 's' : ''}</small></div>
      <div className="room-grid">{deptRooms.map(room => <RoomCard key={room.key} room={room} />)}</div>
    </section>)}
    {!filtered.length && <div className="empty-state">No rooms match these filters.</div>}
  </div>
}
