import { useEffect, useState } from 'react'
import { api } from '../api/client'
import CameraCard from '../components/CameraCard'

export default function LiveCameras() {
  const [cameras, setCameras] = useState([])

  useEffect(() => {
    const load = () => api.cameras.list().then(setCameras)
    load()
    const id = setInterval(load, 8000)
    return () => clearInterval(id)
  }, [])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Live Cameras</h1>
          <div className="page-subtitle">MJPEG feeds, streamed directly from the backend</div>
        </div>
      </div>
      <div className="grid grid-cols-2">
        {cameras.map((cam) => (
          <CameraCard key={cam.id} camera={cam} />
        ))}
      </div>
    </div>
  )
}
