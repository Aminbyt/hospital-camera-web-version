import { useRef, useState } from 'react'

/**
 * Draw a scrub-zone rectangle directly on the live MJPEG feed in the
 * browser. Replaces the old PyQt ROIDrawer/QDialog - the normalized
 * [x1,y1,x2,y2] rectangle (0-1 range, same convention as the original
 * desktop app) is handed to onSave(), which PATCHes it to the camera.
 */
export default function RoiDrawer({ imageSrc, initialRoi, onSave, onCancel }) {
  const wrapRef = useRef(null)
  const [drawing, setDrawing] = useState(false)
  const [start, setStart] = useState(null)
  const [rect, setRect] = useState(
    initialRoi ? { x1: initialRoi[0], y1: initialRoi[1], x2: initialRoi[2], y2: initialRoi[3] } : null
  )

  const toNorm = (e) => {
    const box = wrapRef.current.getBoundingClientRect()
    const x = Math.min(Math.max((e.clientX - box.left) / box.width, 0), 1)
    const y = Math.min(Math.max((e.clientY - box.top) / box.height, 0), 1)
    return { x, y }
  }

  const handleDown = (e) => {
    const p = toNorm(e)
    setStart(p)
    setRect({ x1: p.x, y1: p.y, x2: p.x, y2: p.y })
    setDrawing(true)
  }

  const handleMove = (e) => {
    if (!drawing || !start) return
    const p = toNorm(e)
    setRect({
      x1: Math.min(start.x, p.x), y1: Math.min(start.y, p.y),
      x2: Math.max(start.x, p.x), y2: Math.max(start.y, p.y),
    })
  }

  const handleUp = () => setDrawing(false)

  const save = () => {
    if (!rect) return
    onSave([rect.x1, rect.y1, rect.x2, rect.y2])
  }

  return (
    <div>
      <div
        ref={wrapRef}
        onMouseDown={handleDown}
        onMouseMove={handleMove}
        onMouseUp={handleUp}
        style={{
          position: 'relative', width: '100%', aspectRatio: '4 / 3',
          background: '#0B1310', borderRadius: 8, overflow: 'hidden',
          cursor: 'crosshair', userSelect: 'none',
        }}
      >
        <img src={imageSrc} alt="calibration" style={{ width: '100%', height: '100%', objectFit: 'cover', pointerEvents: 'none' }} />
        {rect && (
          <div style={{
            position: 'absolute',
            left: `${rect.x1 * 100}%`, top: `${rect.y1 * 100}%`,
            width: `${(rect.x2 - rect.x1) * 100}%`, height: `${(rect.y2 - rect.y1) * 100}%`,
            border: '2px solid #ffffff', background: 'rgba(255,255,255,0.12)',
          }} />
        )}
      </div>
      <p className="muted" style={{ fontSize: 12.5, marginTop: 10 }}>
        Click and drag on the frame to draw the valid scrub zone. The top edge of the
        rectangle becomes the sink line used for wash detection.
      </p>
      <div style={{ display: 'flex', gap: 10 }}>
        <button className="btn btn-primary" onClick={save} disabled={!rect}>Save zone</button>
        <button className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  )
}
