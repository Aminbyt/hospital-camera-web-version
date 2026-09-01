import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import RoiDrawer from '../components/RoiDrawer'

export default function CameraDetail() {
  const { id } = useParams()
  const camId = Number(id)
  const [camera, setCamera] = useState(null)
  const [status, setStatus] = useState(null)
  const [settings, setSettings] = useState(null)
  const [calibrating, setCalibrating] = useState(false)
  const [imgKey, setImgKey] = useState(0)

  const loadCamera = () => api.cameras.list().then((all) => setCamera(all.find((c) => c.id === camId)))

  useEffect(() => {
    loadCamera()
    api.settings.get().then(setSettings)
    let alive = true
    const poll = async () => {
      try {
        const s = await api.cameras.status(camId)
        if (alive) setStatus(s)
      } catch {
        if (alive) setStatus(null)
      }
    }
    poll()
    const t = setInterval(poll, 800)
    return () => { alive = false; clearInterval(t) }
  }, [camId])

  if (!camera) return <p className="muted">Loading…</p>

  const maxWash = settings?.max_wash_time ?? 40
  const washPct = status ? Math.min(100, (status.wash_time / maxWash) * 100) : 0

  const saveRoi = async (roi) => {
    await api.cameras.update(camId, { manual_roi: roi })
    setCalibrating(false)
    loadCamera()
  }

  const resetCalibration = async () => {
    await api.cameras.calibrate(camId)
    loadCamera()
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <Link to="/live" className="muted mono" style={{ fontSize: 12 }}>&larr; ALL CAMERAS</Link>
          <h1 className="page-title" style={{ marginTop: 6 }}>{camera.name}</h1>
          <div className="page-subtitle">source: {camera.source}</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: 24, alignItems: 'start' }}>
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {calibrating ? (
            <div style={{ padding: 16 }}>
              <RoiDrawer
                imageSrc={api.streamUrl(camId)}
                initialRoi={camera.manual_roi}
                onSave={saveRoi}
                onCancel={() => setCalibrating(false)}
              />
            </div>
          ) : (
            <div className="cam-video-wrap" style={{ aspectRatio: '16 / 10' }}>
              <img key={imgKey} src={api.streamUrl(camId)} alt={camera.name}
                onError={() => setTimeout(() => setImgKey((k) => k + 1), 2000)} />
              <div className="cam-live-pill">
                <span className={'cam-live-dot' + (status?.connected ? '' : ' off')} />
                {status?.connected ? 'LIVE' : 'OFFLINE'}
              </div>
            </div>
          )}
          {!calibrating && (
            <div style={{ padding: 14, display: 'flex', gap: 10 }}>
              <button className="btn btn-sm" onClick={() => setCalibrating(true)}>Draw manual scrub zone</button>
              <button className="btn btn-sm" onClick={resetCalibration}>Reset to auto zone</button>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-title">Identity</div>
            {status?.is_auth ? (
              <div className="pill pill-ok" style={{ marginTop: 8 }}>{status.user}</div>
            ) : (
              <div className="pill pill-neutral" style={{ marginTop: 8 }}>NOT AUTHENTICATED</div>
            )}
            <div className="muted mono" style={{ fontSize: 11.5, marginTop: 8 }}>{status?.auth_msg}</div>
          </div>

          <div className="card">
            <div className="card-title">PPE Verification</div>
            <div className="cam-tile-meta" style={{ marginTop: 10 }}>
              {camera.check_mask ? (
                <span className={'pill ' + (status?.mask ? 'pill-ok' : 'pill-bad')}>MASK {status?.mask ? 'OK' : 'MISSING'}</span>
              ) : <span className="pill pill-neutral">MASK DISABLED</span>}
              {camera.check_hat ? (
                <span className={'pill ' + (status?.hat ? 'pill-ok' : 'pill-bad')}>HAT {status?.hat ? 'OK' : 'MISSING'}</span>
              ) : <span className="pill pill-neutral">HAT DISABLED</span>}
            </div>
          </div>

          <div className="card">
            <div className="card-title">Hand-Wash Timer</div>
            <div className="mono" style={{ fontSize: 22, fontWeight: 600, marginTop: 6 }}>
              {status ? Math.floor(status.wash_time) : 0}s <span className="muted" style={{ fontSize: 13 }}>/ {maxWash}s</span>
            </div>
            <div className="progress-track" style={{ marginTop: 8 }}>
              <div className="progress-fill" style={{ width: `${washPct}%` }} />
            </div>
            <div className="muted" style={{ fontSize: 12.5, marginTop: 10, whiteSpace: 'pre-line' }}>
              {status?.wash_status || 'STANDBY'}
            </div>
          </div>

          <div className="card" style={{
            textAlign: 'center',
            background: status?.master_ready ? 'var(--brand)' : 'var(--surface)',
            color: status?.master_ready ? '#fff' : 'var(--ink)',
          }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15 }}>
              {status?.master_ready ? 'PROCEED TO OPERATING ROOM' : 'ACTION REQUIRED'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
