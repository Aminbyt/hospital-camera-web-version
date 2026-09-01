"""Dynamic camera registry.

This is the direct replacement for:

    # old config.py
    SINK_CAMERAS = {
        "SINK_1": 1,
        # "SINK_2": "rtsp://...",
    }

Cameras now live in the `cameras` DB table and are added, edited, enabled,
disabled, or removed at any time through the /api/cameras endpoints - no
code changes, no restart, no fixed count of sinks.
"""
import logging
import threading
from typing import Dict, Optional

from app.database import SessionLocal
from app.models import Camera
from app.services.camera_worker import CameraStream

_lock = threading.RLock()
_streams: Dict[int, CameraStream] = {}


def _coerce_source(source: str):
    """A camera source is either a webcam index ("0","1"...) or a URL
    (rtsp://, http://). Never hardcoded which one - inferred per camera."""
    if source.isdigit():
        return int(source)
    return source


def start_all_enabled():
    db = SessionLocal()
    try:
        cameras = db.query(Camera).filter(Camera.enabled == True).all()  # noqa: E712
        for cam in cameras:
            try:
                start_camera(cam)
            except Exception as e:
                # Don't let one bad camera (wrong index, missing model file,
                # unreachable RTSP URL, etc.) prevent the rest from starting.
                logging.error(f"[CAMERA] Failed to start '{cam.name}' (source={cam.source}): {e}")
    finally:
        db.close()


def start_camera(camera: Camera):
    with _lock:
        if camera.id in _streams:
            return _streams[camera.id]
        stream = CameraStream(camera.id, camera.name, _coerce_source(camera.source))
        stream.update_toggles(camera.check_mask, camera.check_hat, camera.check_wash)
        if camera.manual_roi:
            stream.set_manual_roi(camera.manual_roi)
        stream.start()
        _streams[camera.id] = stream
        return stream


def stop_camera(camera_id: int):
    with _lock:
        stream = _streams.pop(camera_id, None)
        if stream:
            stream.stop()


def restart_camera(camera: Camera):
    stop_camera(camera.id)
    return start_camera(camera)


def get_stream(camera_id: int) -> Optional[CameraStream]:
    with _lock:
        return _streams.get(camera_id)


def all_streams():
    with _lock:
        return dict(_streams)


def apply_toggles_to_all(mask: bool, hat: bool, wash: bool):
    with _lock:
        for stream in _streams.values():
            stream.update_toggles(mask, hat, wash)


def stop_all():
    with _lock:
        for stream in list(_streams.values()):
            stream.stop()
        _streams.clear()


import time


def generate_frames(camera_id: int):
    # Fetch the specific camera thread
    worker = get_stream(camera_id)

    while True:
        if not worker:
            break

        # Grab the pre-compressed JPEG from camera_worker.py
        jpeg_bytes = worker.get_jpeg()

        if not jpeg_bytes:
            time.sleep(0.05)
            continue

        # Yield the exact multipart byte structure browsers require for video
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg_bytes + b'\r\n')