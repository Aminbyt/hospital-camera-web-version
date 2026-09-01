import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../api/client'

function StatusPill({ status }) {
  if (!status || !status.connected) return <span className="pill pill-neutral">NO SIGNAL</span>
  if (!status.is_auth) return <span className="pill pill-neutral">IDLE</span>
  if (status.master_ready) return <span className="pill pill-ok">COMPLIANT</span>
  return <span className="pill pill-warn">IN PROGRESS</span>
}

export default function CameraCard({ camera }) {
  const [status, setStatus] = useState(null)
  const [imgKey, setImgKey] = useState(0)

  useEffect(() => {
    let alive = true
    const poll = async () => {
      try {
        const s = await api.cameras.status(camera.id)
        if (alive) setStatus(s)
      } catch {
        if (alive) setStatus(null)
      }
    }
    poll()
    const id = setInterval(poll, 1500)
    return () => { alive = false; clearInterval(id) }
  }, [camera.id])

  return (
    <div className="cam-tile">
      <Link to={`/cameras/${camera.id}`} style={{ textDecoration: 'none', color: 'inherit' }}>
        <div className="cam-video-wrap">
          {camera.enabled ? (
            <img
              key={imgKey}
              src={api.streamUrl(camera.id)}
              alt={camera.name}
              onError={() => setTimeout(() => setImgKey((k) => k + 1), 2000)}
            />
          ) : (
            <div className="cam-video-placeholder">Camera disabled<br />Enable it from Settings</div>
          )}
          <div className="cam-live-pill">
            <span className={'cam-live-dot' + (status?.connected ? '' : ' off')} />
            {status?.connected ? 'LIVE' : 'OFFLINE'}
          </div>
        </div>
      </Link>
      <div className="cam-tile-body">
        <div className="cam-tile-name">
          <span>{camera.name}</span>
          <StatusPill status={status} />
        </div>
        <div className="muted mono" style={{ fontSize: 11, marginTop: 4 }}>
          {status?.user && status.user !== 'EMPTY' ? status.user : 'No user detected'}
        </div>
        <div className="cam-tile-meta">
          {camera.check_mask && <span className="pill pill-neutral">MASK</span>}
          {camera.check_hat && <span className="pill pill-neutral">HAT</span>}
          {camera.check_wash && <span className="pill pill-neutral">WASH</span>}
        </div>
      </div>
    </div>
  )
}
