import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services import camera_manager

router = APIRouter(prefix="/api/stream", tags=["stream"])


_PLACEHOLDER_WAIT = 0.03


def _mjpeg_generator(camera_id: int):
    boundary = b"--frame"
    while True:
        stream = camera_manager.get_stream(camera_id)
        if not stream:
            break
        jpeg = stream.get_jpeg()
        if jpeg is not None:
            yield (boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n")
        time.sleep(_PLACEHOLDER_WAIT)



# @router.get("/sink/{camera_id}/live")
# def stream_camera(camera_id: str):
#     return StreamingResponse(
#         camera_manager.generate_frames(camera_id),
#         media_type="multipart/x-mixed-replace; boundary=frame"
#     )

@router.get("/sink/{camera_id}/live")
def stream_camera(camera_id: int):
    return StreamingResponse(
        camera_manager.generate_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )