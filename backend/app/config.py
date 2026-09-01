"""
Runtime configuration.

Everything that used to be hardcoded in the old desktop config.py
(paths, camera list, wash timings, AI thresholds, bot credentials) is now
either:
  1. Read from environment variables / .env  (deployment-level settings,
     e.g. where files live on THIS machine), or
  2. Stored in the database `settings` table and editable live from the
     Settings page in the web UI (behavioural settings, e.g. thresholds,
     bot credentials, wash timers).

Nothing about camera identity/source is here anymore at all - cameras are
rows in the `cameras` table, managed entirely through the API/UI.
"""
import os
from pydantic_settings import BaseSettings


class EnvSettings(BaseSettings):
    DATA_ROOT: str = "./data"
    DATABASE_URL: str = "sqlite:///./data/hospital_ai.db"
    YOLO_MODEL_PATH: str = "./models/best_openvino_model/"
    WHO_MODEL_PATH: str = "./models/who_cnn_lstm_model.onnx"
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    BOT_API_URL: str = ""
    BOT_CHAT_ID: str = ""
    BOT_TIMEOUT: int = 3

    class Config:
        env_file = ".env"


env = EnvSettings()

# Derived, always-needed folders (created on startup, never hardcoded to a
# specific OS user path like the old `os.environ['USERPROFILE']\Desktop`)
REG_PATH = os.path.join(env.DATA_ROOT, "REGISTER_PERSONS")
INFO_PATH = os.path.join(env.DATA_ROOT, "INFORMATION")
LOGS_PATH = os.path.join(env.DATA_ROOT, "LOGS")
RECORDINGS_PATH = os.path.join(env.DATA_ROOT, "RECORDINGS")


def ensure_directories():
    for p in (env.DATA_ROOT, REG_PATH, INFO_PATH, LOGS_PATH, RECORDINGS_PATH):
        os.makedirs(p, exist_ok=True)


# --- Default behavioural settings (seeded into DB `settings` table on first
# boot, then editable live from the Settings page - see services/settings_store.py) ---
DEFAULT_SETTINGS = {
    "yolo_conf_threshold": 0.6,
    "face_detection_confidence": 0.5,
    "hand_detection_confidence": 0.4,
    "hand_tracking_confidence": 0.4,
    "max_num_hands": 2,
    "min_wash_time": 20,
    "max_wash_time": 40,
    "auth_cooldown": 2.0,
    "presence_timeout": 6.0,
    "touch_timeout": 2.5,
    "wrist_distance_threshold": 65,
    "hand_size_multiplier": 2.5,
    "min_bubble_radius": 250,
    "bot_api_url": env.BOT_API_URL,
    "bot_chat_id": env.BOT_CHAT_ID,
    "bot_timeout": env.BOT_TIMEOUT,
    "check_mask_default": True,
    "check_hat_default": True,
    "check_wash_default": True,
}
