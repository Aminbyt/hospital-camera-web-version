import { useEffect, useState } from 'react'
import { api } from '../api/client'

function CameraForm({ onCreated }) {
  const [name, setName] = useState('')
  const [source, setSource] = useState('')
  const [room, setRoom] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      await api.cameras.create({ name, source, room })
      setName(''); setSource(''); setRoom('')
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={submit} className="card">
      <div className="card-title">Add a camera</div>
      <p className="muted" style={{ fontSize: 12.5, marginTop: 2 }}>
        Works for any number of sinks. Use a webcam index ("0", "1"...) for a
        USB camera, or a full RTSP/HTTP URL for a network camera.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14, marginTop: 14 }}>
        <div className="field">
          <label>Camera name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="SINK 1" required />
        </div>
        <div className="field">
          <label>Source (index or URL)</label>
          <input type="text" value={source} onChange={(e) => setSource(e.target.value)}
            placeholder="0  or  rtsp://user:pass@ip:554/stream" required />
        </div>
        <div className="field">
          <label>Room / Location</label>
          <input type="text" value={room} onChange={(e) => setRoom(e.target.value)}
            placeholder="OR 3, Ward B…" />
        </div>
      </div>
      {error && <p style={{ color: 'var(--danger)', fontSize: 12.5 }}>{error}</p>}
      <button className="btn btn-primary" disabled={saving}>{saving ? 'Adding…' : 'Add camera'}</button>
    </form>
  )
}

function CameraRow({ cam, onChanged }) {
  const [busy, setBusy] = useState(false)

  const toggle = async (field) => {
    setBusy(true)
    await api.cameras.update(cam.id, { [field]: !cam[field] })
    onChanged()
    setBusy(false)
  }

  const remove = async () => {
    if (!confirm(`Remove camera "${cam.name}"? This stops its stream and deletes its config.`)) return
    setBusy(true)
    await api.cameras.remove(cam.id)
    onChanged()
  }

  return (
    <tr>
      <td style={{ fontWeight: 600 }}>{cam.name}</td>
      <td className="mono">{cam.source}</td>
      <td>{cam.room || <span className="muted">—</span>}</td>
      <td>
        <span className={'pill ' + (cam.enabled ? 'pill-ok' : 'pill-neutral')}>
          {cam.enabled ? 'ENABLED' : 'DISABLED'}
        </span>
      </td>
      <td>
        <div style={{ display: 'flex', gap: 6 }}>
          {['check_mask', 'check_hat', 'check_wash'].map((f) => (
            <button key={f} className="btn btn-sm" disabled={busy} onClick={() => toggle(f)}
              style={{ opacity: cam[f] ? 1 : 0.45 }}>
              {f.replace('check_', '').toUpperCase()}
            </button>
          ))}
        </div>
      </td>
      <td>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn btn-sm" disabled={busy} onClick={() => toggle('enabled')}>
            {cam.enabled ? 'Disable' : 'Enable'}
          </button>
          <button className="btn btn-sm btn-danger" disabled={busy} onClick={remove}>Remove</button>
        </div>
      </td>
    </tr>
  )
}

function RegistrationPanel({ cameras }) {
  const [cameraId, setCameraId] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [role, setRole] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  const capture = async (e) => {
    e.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      const res = await api.registration.capture({
        camera_id: Number(cameraId), first_name: firstName, last_name: lastName, role,
      })
      setResult({ ok: true, message: `Saved ${res.file_name} for ${res.full_name} (angle #${res.angle_saved})` })
      setFirstName(''); setLastName(''); setRole('')
    } catch (err) {
      setResult({ ok: false, message: err.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="card-title">Register staff</div>
      <p className="muted" style={{ fontSize: 12.5 }}>
        Captures the CURRENT live frame from the selected camera as a face reference photo.
      </p>
      <form onSubmit={capture} style={{ marginTop: 10 }}>
        <div className="field">
          <label>Camera to capture from</label>
          <select value={cameraId} onChange={(e) => setCameraId(e.target.value)} required>
            <option value="">Select a camera…</option>
            {cameras.map((c) => <option key={c.id} value={c.id}>{c.name}{c.room ? ` — ${c.room}` : ''}</option>)}
          </select>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div className="field">
            <label>First name</label>
            <input value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
          </div>
          <div className="field">
            <label>Last name</label>
            <input value={lastName} onChange={(e) => setLastName(e.target.value)} required />
          </div>
        </div>
        <div className="field">
          <label>Role</label>
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Surgeon, Nurse…" />
        </div>
        <button className="btn btn-primary" disabled={busy}>{busy ? 'Capturing…' : 'Capture & save'}</button>
      </form>
      {result && (
        <p style={{ marginTop: 10, fontSize: 12.5, color: result.ok ? 'var(--success)' : 'var(--danger)' }}>
          {result.message}
        </p>
      )}
      <button
        type="button"
        className="btn btn-sm"
        style={{ marginTop: 10 }}
        onClick={() => api.registration.resetCache().then(() => alert('Face cache rebuilt from disk.'))}
      >
        Rebuild face recognition cache
      </button>
    </div>
  )
}

export default function Settings() {
  const [cameras, setCameras] = useState([])
  const [settings, setSettings] = useState(null)
  const [savingSettings, setSavingSettings] = useState(false)

  const loadCameras = () => api.cameras.list().then(setCameras)
  const loadSettings = () => api.settings.get().then(setSettings)

  useEffect(() => { loadCameras(); loadSettings() }, [])

  const saveSettings = async (e) => {
    e.preventDefault()
    setSavingSettings(true)
    await api.settings.update(settings)
    setSavingSettings(false)
  }

  const num = (v) => (v === '' ? '' : Number(v))

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <div className="page-subtitle">Cameras, thresholds and bot alerts — all live, nothing hardcoded</div>
        </div>
      </div>

      <div className="card-title" style={{ marginBottom: 10 }}>Cameras</div>
      {cameras.length > 0 && (
        <table className="data-table" style={{ marginBottom: 20 }}>
          <thead>
            <tr><th>Name</th><th>Source</th><th>Room</th><th>Status</th><th>Checks</th><th></th></tr>
          </thead>
          <tbody>
            {cameras.map((c) => <CameraRow key={c.id} cam={c} onChanged={loadCameras} />)}
          </tbody>
        </table>
      )}
      <CameraForm onCreated={loadCameras} />

      <div className="section-divider" />

      {settings && (
        <form onSubmit={saveSettings}>
          <div className="card-title" style={{ marginBottom: 10 }}>Detection defaults</div>
          <div className="card" style={{ marginBottom: 20 }}>
            <label className="checkbox-row">
              <input type="checkbox" checked={settings.check_mask_default}
                onChange={(e) => setSettings({ ...settings, check_mask_default: e.target.checked })} />
              Verify medical mask by default
            </label>
            <label className="checkbox-row">
              <input type="checkbox" checked={settings.check_hat_default}
                onChange={(e) => setSettings({ ...settings, check_hat_default: e.target.checked })} />
              Verify surgical hat by default
            </label>
            <label className="checkbox-row">
              <input type="checkbox" checked={settings.check_wash_default}
                onChange={(e) => setSettings({ ...settings, check_wash_default: e.target.checked })} />
              Verify hand washing by default
            </label>
          </div>

          <div className="card-title" style={{ marginBottom: 10 }}>Wash timing & thresholds</div>
          <div className="card" style={{ marginBottom: 20, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
            <div className="field">
              <label>Minimum wash time (s)</label>
              <input type="number" value={settings.min_wash_time}
                onChange={(e) => setSettings({ ...settings, min_wash_time: num(e.target.value) })} />
            </div>
            <div className="field">
              <label>Maximum wash time (s)</label>
              <input type="number" value={settings.max_wash_time}
                onChange={(e) => setSettings({ ...settings, max_wash_time: num(e.target.value) })} />
            </div>
            <div className="field">
              <label>Presence timeout (s)</label>
              <input type="number" value={settings.presence_timeout}
                onChange={(e) => setSettings({ ...settings, presence_timeout: num(e.target.value) })} />
            </div>
            <div className="field">
              <label>YOLO confidence threshold</label>
              <input type="number" step="0.05" value={settings.yolo_conf_threshold}
                onChange={(e) => setSettings({ ...settings, yolo_conf_threshold: num(e.target.value) })} />
            </div>
            <div className="field">
              <label>Hand detection confidence</label>
              <input type="number" step="0.05" value={settings.hand_detection_confidence}
                onChange={(e) => setSettings({ ...settings, hand_detection_confidence: num(e.target.value) })} />
            </div>
            <div className="field">
              <label>Face detection confidence</label>
              <input type="number" step="0.05" value={settings.face_detection_confidence}
                onChange={(e) => setSettings({ ...settings, face_detection_confidence: num(e.target.value) })} />
            </div>
          </div>

          <div className="card-title" style={{ marginBottom: 10 }}>Bot notifications</div>
          <div className="card" style={{ marginBottom: 20, display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 14 }}>
            <div className="field">
              <label>Bot API URL</label>
              <input type="text" value={settings.bot_api_url}
                onChange={(e) => setSettings({ ...settings, bot_api_url: e.target.value })}
                placeholder="https://tapi.bale.ai/.../sendMessage" />
            </div>
            <div className="field">
              <label>Chat ID</label>
              <input type="text" value={settings.bot_chat_id}
                onChange={(e) => setSettings({ ...settings, bot_chat_id: e.target.value })} />
            </div>
            <div className="field">
              <label>Timeout (s)</label>
              <input type="number" value={settings.bot_timeout}
                onChange={(e) => setSettings({ ...settings, bot_timeout: num(e.target.value) })} />
            </div>
          </div>

          <button className="btn btn-primary" disabled={savingSettings}>
            {savingSettings ? 'Saving…' : 'Save all settings'}
          </button>
        </form>
      )}

      <div className="section-divider" />
      <RegistrationPanel cameras={cameras} />
    </div>
  )
}
