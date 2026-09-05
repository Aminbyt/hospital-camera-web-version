import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { getCameraMeta } from '../utils/hospitalMeta'

function StatusPill({ status }) {
  if (!status?.connected) return <span className="pill pill-neutral">OFFLINE</span>
  if (!status.is_auth) return <span className="pill pill-neutral">IDLE</span>
  if (status.master_ready) return <span className="pill pill-ok">COMPLIANT</span>
  return <span className="pill pill-warn">IN PROGRESS</span>
}

function fmtSeconds(v = 0) {
  const s = Math.max(0, Math.floor(v))
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

export default function CameraCard({ camera, initialStatus = null, compact = false }) {
  const [status, setStatus] = useState(initialStatus)
  const [imgKey, setImgKey] = useState(0)
  const meta = getCameraMeta(camera)

  useEffect(() => {
    let alive = true
    const poll = async () => {
      try { const s = await api.cameras.status(camera.id); if (alive) setStatus(s) }
      catch { if (alive) setStatus(null) }
    }
    poll(); const id = setInterval(poll, 1500)
    return () => { alive = false; clearInterval(id) }
  }, [camera.id])

  const openCamera = () => window.open(`/cameras/${camera.id}`, '_blank', 'noopener,noreferrer')
  const who = status?.user && status.user !== 'EMPTY' ? status.user : 'No active user'

  return (
    <article className={'camera-card' + (compact ? ' compact' : '')}>
      <button className="camera-open-area" onClick={openCamera} title="Open camera in new tab">
        <div className="cam-video-wrap">
          {camera.enabled ? (
            <img key={imgKey} src={api.streamUrl(camera.id)} alt={camera.name}
              onError={() => setTimeout(() => setImgKey((k) => k + 1), 2000)} />
          ) : <div className="cam-video-placeholder">NO SIGNAL<br />Camera disabled</div>}
          <div className="cam-live-pill"><span className={'cam-live-dot' + (status?.connected ? '' : ' off')} />{status?.connected ? 'LIVE' : 'OFFLINE'}</div>
          <div className="video-timestamp mono">{new Date().toLocaleTimeString()}</div>
        </div>
      </button>
      <div className="camera-card-body">
        <div className="camera-card-head">
          <div><h3>{camera.name}</h3><p>{meta.purpose}</p></div><StatusPill status={status} />
        </div>
        {!compact && <>
          <div className="camera-health-row"><span>Camera health</span><strong className={status?.connected ? 'ok-text' : 'bad-text'}>{status?.connected ? 'Healthy' : 'Connection lost'}</strong></div>
          <div className="camera-user"><span className="label">CURRENT USER</span><strong>{who}</strong><small>{status?.is_auth ? '✓ Authenticated' : 'Waiting for authentication'}</small></div>
          <div className="ai-mini-grid">
            <div><span>Mask</span><strong className={status?.mask ? 'ok-text' : 'muted'}>{camera.check_mask ? (status?.mask ? '✓ PASS' : '—') : 'OFF'}</strong></div>
            <div><span>Hat</span><strong className={status?.hat ? 'ok-text' : 'muted'}>{camera.check_hat ? (status?.hat ? '✓ PASS' : '—') : 'OFF'}</strong></div>
            <div><span>Hand Wash</span><strong>{fmtSeconds(status?.wash_time)}</strong></div>
            <div><span>WHO Steps</span><strong>{status?.master_ready ? '6 / 6' : status?.is_auth ? 'Monitoring' : '—'}</strong></div>
          </div>
        </>}
      </div>
    </article>
  )
}
