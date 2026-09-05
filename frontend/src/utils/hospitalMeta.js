const KEY = 'akam-smart-scrub-camera-meta-v1'

const defaults = {
  department: 'Unassigned',
  floor: 'Unassigned',
  type: 'Webcam',
  purpose: 'Sink Monitoring Camera',
}

function readAll() {
  try { return JSON.parse(localStorage.getItem(KEY) || '{}') } catch { return {} }
}

function writeAll(value) {
  localStorage.setItem(KEY, JSON.stringify(value))
  window.dispatchEvent(new Event('akam-meta-updated'))
}

function inferDepartment(room = '') {
  const s = room.toLowerCase()
  if (s.includes('operat') || s.includes('surgery') || s.includes('or ')) return 'Surgery'
  if (s.includes('icu')) return 'ICU'
  if (s.includes('ccu')) return 'CCU'
  if (s.includes('nurs')) return 'Nursing'
  if (s.includes('recover')) return 'Recovery'
  if (s.includes('pharm')) return 'Pharmacy'
  return 'Unassigned'
}

export function getCameraMeta(camera) {
  const saved = readAll()[camera.id] || {}
  return {
    ...defaults,
    department: saved.department || inferDepartment(camera.room) || defaults.department,
    floor: saved.floor || defaults.floor,
    type: saved.type || (String(camera.source).includes('://') ? 'Dahua / IP Camera' : 'Webcam'),
    purpose: saved.purpose || defaults.purpose,
    ...saved,
  }
}

export function setCameraMeta(cameraId, patch) {
  const all = readAll()
  all[cameraId] = { ...(all[cameraId] || {}), ...patch }
  writeAll(all)
  return all[cameraId]
}

export function removeCameraMeta(cameraId) {
  const all = readAll()
  delete all[cameraId]
  writeAll(all)
}

export function withMeta(camera) {
  return { ...camera, meta: getCameraMeta(camera) }
}

export function groupRooms(cameras) {
  const map = new Map()
  cameras.forEach((raw) => {
    const c = raw.meta ? raw : withMeta(raw)
    const room = c.room || 'Unassigned Room'
    const key = `${c.meta.department}::${room}`
    if (!map.has(key)) {
      map.set(key, {
        key,
        slug: encodeURIComponent(key),
        name: room,
        department: c.meta.department,
        floor: c.meta.floor,
        cameras: [],
      })
    }
    map.get(key).cameras.push(c)
  })
  return [...map.values()].sort((a, b) =>
    a.department.localeCompare(b.department) || a.name.localeCompare(b.name)
  )
}

export function decodeRoomSlug(slug) {
  try {
    const value = decodeURIComponent(slug)
    const [department, ...rest] = value.split('::')
    return { department, name: rest.join('::') }
  } catch {
    return { department: '', name: '' }
  }
}
