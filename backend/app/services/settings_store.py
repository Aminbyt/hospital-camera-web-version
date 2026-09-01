"""
Central place every module reads *behavioural* settings from
(wash timers, AI thresholds, bot credentials) instead of importing
hardcoded constants from config.py like the old app did.

Backed by the `settings` DB table so changes made on the Settings page
apply immediately to every running camera worker, no restart required.
"""
import threading
from app.database import SessionLocal
from app.models import SettingKV
from app.config import DEFAULT_SETTINGS

_lock = threading.RLock()
_cache = {}


def seed_defaults():
    db = SessionLocal()
    try:
        existing = {row.key for row in db.query(SettingKV.key).all()}
        for key, value in DEFAULT_SETTINGS.items():
            if key not in existing:
                db.add(SettingKV(key=key, value=value))
        db.commit()
    finally:
        db.close()
    reload_cache()


def reload_cache():
    with _lock:
        db = SessionLocal()
        try:
            _cache.clear()
            for row in db.query(SettingKV).all():
                _cache[row.key] = row.value
        finally:
            db.close()


def get(key, default=None):
    with _lock:
        if not _cache:
            reload_cache()
        return _cache.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))


def get_all():
    with _lock:
        if not _cache:
            reload_cache()
        return dict(_cache)


def set_many(values: dict):
    db = SessionLocal()
    try:
        for key, value in values.items():
            row = db.get(SettingKV, key)
            if row is None:
                row = SettingKV(key=key, value=value)
                db.add(row)
            else:
                row.value = value
        db.commit()
    finally:
        db.close()
    reload_cache()
