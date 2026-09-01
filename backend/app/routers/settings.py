from fastapi import APIRouter
from app.services import settings_store as cfg
from app.services import camera_manager
from app.schemas import SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings():
    return cfg.get_all()


@router.put("")
def update_settings(payload: SettingsUpdate):
    cfg.set_many(payload.values)

    # Global default detection toggles apply live to every running camera,
    # mirroring the old main_app.py `master_update_toggles()` behaviour.
    if any(k in payload.values for k in ("check_mask_default", "check_hat_default", "check_wash_default")):
        settings = cfg.get_all()
        camera_manager.apply_toggles_to_all(
            settings.get("check_mask_default", True),
            settings.get("check_hat_default", True),
            settings.get("check_wash_default", True),
        )
    return cfg.get_all()
