from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Camera
from app.schemas import CameraCreate, CameraUpdate, CameraOut
from app.services import camera_manager

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


def _to_out(cam: Camera) -> CameraOut:
    stream = camera_manager.get_stream(cam.id)
    connected = bool(stream and stream.get_status().get("connected"))
    return CameraOut(
        id=cam.id, name=cam.name, source=cam.source, room=cam.room, enabled=cam.enabled,
        check_mask=cam.check_mask, check_hat=cam.check_hat, check_wash=cam.check_wash,
        manual_roi=cam.manual_roi, sink_y_start=cam.sink_y_start, connected=connected,
    )


@router.get("", response_model=list[CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    return [_to_out(c) for c in db.query(Camera).all()]


@router.post("", response_model=CameraOut)
def create_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    if db.query(Camera).filter(Camera.name == payload.name).first():
        raise HTTPException(400, "A camera with that name already exists.")
    cam = Camera(**payload.model_dump())
    db.add(cam)
    db.commit()
    db.refresh(cam)
    if cam.enabled:
        camera_manager.start_camera(cam)
    return _to_out(cam)


@router.patch("/{camera_id}", response_model=CameraOut)
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(cam, key, value)
    db.commit()
    db.refresh(cam)

    # Apply live, without requiring a restart of the backend
    stream = camera_manager.get_stream(camera_id)
    if "enabled" in data:
        if cam.enabled:
            camera_manager.start_camera(cam)
        else:
            camera_manager.stop_camera(camera_id)
    if stream:
        if any(k in data for k in ("check_mask", "check_hat", "check_wash")):
            stream.update_toggles(cam.check_mask, cam.check_hat, cam.check_wash)
        if "manual_roi" in data:
            stream.set_manual_roi(cam.manual_roi)
        if "source" in data or "name" in data:
            camera_manager.restart_camera(cam)

    return _to_out(cam)


@router.delete("/{camera_id}")
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    camera_manager.stop_camera(camera_id)
    db.delete(cam)
    db.commit()
    return {"ok": True}


@router.post("/{camera_id}/calibrate")
def calibrate_camera(camera_id: int, db: Session = Depends(get_db)):
    """Clears manual ROI and lets the auto zone-split logic take over again."""
    cam = db.get(Camera, camera_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    cam.manual_roi = None
    cam.sink_y_start = None
    db.commit()
    stream = camera_manager.get_stream(camera_id)
    if stream:
        stream.trigger_calibration()
    return {"ok": True}


@router.get("/{camera_id}/status")
def camera_status(camera_id: int):
    stream = camera_manager.get_stream(camera_id)
    if not stream:
        raise HTTPException(404, "Camera is not running")
    return stream.get_status()