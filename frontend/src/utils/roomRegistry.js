const KEY = 'akam-smart-scrub-rooms-v1'

function read() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(value) ? value : []
  } catch { return [] }
}

function write(rooms) {
  localStorage.setItem(KEY, JSON.stringify(rooms))
  window.dispatchEvent(new Event('akam-rooms-updated'))
  return rooms
}

function roomId(name) {
  return String(name || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-')
}

export function getRooms() {
  return read().sort((a,b) => (a.department || '').localeCompare(b.department || '') || a.name.localeCompare(b.name))
}

export function addRoom(room) {
  const rooms = read()
  const name = String(room.name || '').trim()
  if (!name) throw new Error('Room name is required')
  if (rooms.some(r => r.name.toLowerCase() === name.toLowerCase())) throw new Error('A room with this name already exists')
  rooms.push({
    id: roomId(name),
    name,
    department: String(room.department || 'General').trim() || 'General',
    floor: String(room.floor || '').trim(),
    area: String(room.area || '').trim(),
  })
  return write(rooms)
}

export function updateRoom(id, patch) {
  const rooms = read()
  const idx = rooms.findIndex(r => r.id === id)
  if (idx < 0) return rooms
  const name = String(patch.name ?? rooms[idx].name).trim()
  rooms[idx] = { ...rooms[idx], ...patch, name, id: roomId(name) }
  return write(rooms)
}

export function removeRoom(id) {
  return write(read().filter(r => r.id !== id))
}

export function findRoom(name) {
  return read().find(r => r.name === name) || null
}

export function syncRoomsFromCameras(cameras = []) {
  const rooms = read()
  let changed = false
  for (const c of cameras) {
    const name = String(c.room || '').trim()
    if (!name || rooms.some(r => r.name.toLowerCase() === name.toLowerCase())) continue
    rooms.push({ id: roomId(name), name, department: 'Imported / Unassigned', floor: '', area: '' })
    changed = true
  }
  if (changed) write(rooms)
  return rooms
}
