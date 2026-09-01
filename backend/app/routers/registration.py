import os
import json
import cv2
import numpy as np
from fastapi import APIRouter, HTTPException

from app.config import REG_PATH
from app.ai.ai_models import add_single_face_to_cache, reset_face_cache
from app.schemas import RegisterStaffRequest
from app.services import camera_manager 

router = APIRouter(prefix="/api/registration", tags=["registration"])


@router.post("/capture")
def register_staff(payload: RegisterStaffRequest):
    """Grabs the CURRENT live frame from the chosen camera and saves it as a
    new reference photo - same folder/JSON format as the original desktop
    app's register_new_user(), so old staff data keeps working."""
    stream = camera_manager.get_stream(payload.camera_id)
    if not stream:
        raise HTTPException(404, "Selected camera is not running.")

    jpeg = stream.get_jpeg()
    if jpeg is None:
        raise HTTPException(400, "No frame available yet from that camera - wait a moment and retry.")

    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)

    fname = payload.first_name.strip().upper()
    lname = payload.last_name.strip().upper()
    role = (payload.role or "N/A").strip().title() or "N/A"
    if not fname or not lname:
        raise HTTPException(400, "First and last name are required.")

    clean_folder_name = f"{fname}_{lname}".replace(" ", "_")
    user_dir = os.path.join(REG_PATH, clean_folder_name)
    os.makedirs(user_dir, exist_ok=True)

    info_path = os.path.join(user_dir, "user_info.json")
    with open(info_path, "w") as f:
        json.dump({"role": role}, f, indent=4)

    existing_photos = [f for f in os.listdir(user_dir) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    next_angle_num = len(existing_photos) + 1
    file_name = f"angle_{next_angle_num}.jpg"
    save_path = os.path.join(user_dir, file_name)
    cv2.imwrite(save_path, frame)

    add_single_face_to_cache(clean_folder_name, save_path)

    return {
        "ok": True,
        "full_name": f"{fname} {lname}",
        "role": role,
        "angle_saved": next_angle_num,
        "file_name": file_name,
    }


@router.post("/reset-cache")
def reset_cache():
    reset_face_cache()
    return {"ok": True}


@router.get("/staff")
def list_staff():
    if not os.path.exists(REG_PATH):
        return []
    staff = []
    for folder in sorted(os.listdir(REG_PATH)):
        person_dir = os.path.join(REG_PATH, folder)
        if not os.path.isdir(person_dir):
            continue
        role = "N/A"
        info_file = os.path.join(person_dir, "user_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file) as f:
                    role = json.load(f).get("role", "N/A")
            except Exception:
                pass
        photos = [p for p in os.listdir(person_dir) if p.lower().endswith((".jpg", ".jpeg", ".png"))]
        staff.append({"name": folder.replace("_", " "), "role": role, "photo_count": len(photos)})
    return staff
