"""Session logging + bot notifications + session state.

Ported from the original data_logger.py. The *fields and trigger logic*
are identical to the original (same wash_status/mask_status/hat_status/
all_steps computation happens in camera_worker.py exactly like it did in
camrea_worker.py). The only change: instead of writing an Excel file per
staff member plus a master-daily Excel file, we write one row to the
`events` SQLite table (queryable instantly by the Events page, and still
exportable to Excel on demand - see routers/events.py).
"""
import os
import json
import time
import requests

from app.config import env, REG_PATH
from app.database import SessionLocal
from app.models import Event, AlertLog
from app.services import settings_store as cfg


class DataLogger:

    @staticmethod
    def get_user_role(current_user):
        """Reads stored user role from their folder's user_info.json - same
        file format as the original desktop app so old staff folders still work."""
        if not current_user:
            return "N/A"
        clean_name = current_user.replace(" ", "_")
        folder_underscores = os.path.join(REG_PATH, clean_name)
        folder_spaces = os.path.join(REG_PATH, current_user)
        person_dir = folder_underscores if os.path.exists(folder_underscores) else folder_spaces
        info_file = os.path.join(person_dir, "user_info.json")

        if os.path.exists(info_file):
            try:
                with open(info_file, 'r') as f:
                    return json.load(f).get("role", "N/A")
            except Exception:
                pass
        return "N/A"

    def log_session(self, camera_id, camera_name, current_user, login_time,
                     wash_status, mask_status, hat_status, all_steps, wash_duration):
        if not current_user:
            return False
        try:
            date_str = time.strftime("%Y-%m-%d")
            role = self.get_user_role(current_user)
            parts = current_user.split(" ", 1)
            fname = parts[0] if len(parts) > 0 else "UNKNOWN"
            lname = parts[1] if len(parts) > 1 else ""

            db = SessionLocal()
            try:
                event = Event(
                    camera_id=camera_id,
                    camera_name=camera_name,
                    date=date_str,
                    time=login_time,
                    first_name=fname,
                    last_name=lname,
                    role=role,
                    mask=mask_status,
                    hat=hat_status,
                    washing_complete=wash_status,
                    wash_duration=int(wash_duration),
                    all_who_steps=all_steps,
                )
                db.add(event)
                db.commit()
            finally:
                db.close()

            print(f"[LOG] Saved visit for {current_user} ({role}) - Duration: {int(wash_duration)}s")
            return True
        except Exception as e:
            print(f"[ERROR] Could not save event: {e}")
            return False

    def send_bot_notification(self, camera_name, current_user, login_time,
                               wash_status, mask_status, hat_status, all_steps, wash_duration):
        bot_api_url = cfg.get("bot_api_url")
        bot_chat_id = cfg.get("bot_chat_id")
        bot_timeout = cfg.get("bot_timeout", 3)
        role = self.get_user_role(current_user)

        bot_message = (
            f"Smart PPE Alert\n"
            f"Sink: {camera_name}\n"
            f"User: {current_user}\n"
            f"Role: {role}\n"
            f"Time: {login_time}\n"
            f"Mask: {mask_status}\n"
            f"Hat: {hat_status}\n"
            f"Washing Complete: {wash_status}\n"
            f"Wash Duration: {int(wash_duration)}s\n"
            f"All WHO Steps: {all_steps}"
        )

        delivered = False
        if bot_api_url and bot_chat_id:
            try:
                payload = {"chat_id": bot_chat_id, "text": bot_message}
                response = requests.post(bot_api_url, json=payload, timeout=bot_timeout)
                delivered = response.status_code == 200
            except Exception:
                delivered = False

        db = SessionLocal()
        try:
            db.add(AlertLog(camera_name=camera_name, message=bot_message,
                             level="info", delivered=delivered))
            db.commit()
        finally:
            db.close()
        return delivered

    def log_and_notify(self, camera_id, camera_name, current_user, login_time,
                        wash_status, mask_status, hat_status, all_steps, wash_duration):
        self.log_session(camera_id, camera_name, current_user, login_time,
                          wash_status, mask_status, hat_status, all_steps, wash_duration)
        self.send_bot_notification(camera_name, current_user, login_time,
                                    wash_status, mask_status, hat_status, all_steps, wash_duration)


class UserSessionManager:
    """Manages user authentication and session state - identical logic to
    the original, thresholds now read live from settings_store."""

    def __init__(self):
        self.current_user = None
        self.login_time = None
        self.is_authenticating = False
        self.last_person_seen_time = time.time()
        self.last_auth_attempt_time = 0

    def set_user(self, user_name):
        self.current_user = user_name.replace("_", " ")
        self.login_time = time.strftime("%H:%M:%S")
        self.last_person_seen_time = time.time()

    def clear_user(self):
        self.current_user = None
        self.login_time = None

    def is_authenticated(self):
        return self.current_user is not None

    def check_presence_timeout(self):
        if not self.is_authenticated():
            return False
        return (time.time() - self.last_person_seen_time) > cfg.get("presence_timeout")

    def can_attempt_auth(self):
        return (time.time() - self.last_auth_attempt_time) >= cfg.get("auth_cooldown")

    def set_auth_attempt(self):
        self.last_auth_attempt_time = time.time()

    def update_presence(self):
        self.last_person_seen_time = time.time()
