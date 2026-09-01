import { useEffect, useState } from 'react'
import { api } from '../api/client'
import CameraCard from '../components/CameraCard'

export default function Dashboard() {
  const [cameras, setCameras] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.cameras.list().then(setCameras).finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Ward Overview</h1>
          <div className="page-subtitle">{cameras.length} camera{cameras.length !== 1 ? 's' : ''} configured</div>
        </div>
      </div>

      {loading && <p className="muted">Loading cameras…</p>}

      {!loading && cameras.length === 0 && (
        <div className="empty-state">
          No cameras yet. Add your first camera from the Settings page — nothing is
          hardcoded, so any webcam index or RTSP/HTTP URL will work.
        </div>
      )}

      <div className="grid grid-cols-3">
        {cameras.map((cam) => (
          <CameraCard key={cam.id} camera={cam} />
        ))}
      </div>
    </div>
  )
}
