import time
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class Camera(Base):
    """
    Replaces the old `config.SINK_CAMERAS = {"SINK_1": 1, ...}` hardcoded dict.
    Cameras are now added/edited/removed at runtime through the API/UI -
    zero code changes or restarts needed to add a 6th, 7th, ... camera.
    """
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    # Accepts a webcam index ("0", "1"...) OR a full RTSP/HTTP stream URL -
    # exactly like the old ZeroLatencyGrabber(src) did, just configurable.
    source = Column(String, nullable=False)
    enabled = Column(Boolean, default=True)

    # Free-text location label, e.g. "OR 3" / "Ward B Scrub Sink" - purely
    # informational, shown in the UI so staff can tell cameras apart.
    room = Column(String, nullable=True)

    check_mask = Column(Boolean, default=True)
    check_hat = Column(Boolean, default=True)
    check_wash = Column(Boolean, default=True)

    # Manual scrub-zone ROI, normalized [x1,y1,x2,y2] 0-1 (set from the
    # frontend's canvas ROI drawer - replaces the old PyQt ROIDrawer dialog)
    manual_roi = Column(JSON, nullable=True)
    sink_y_start = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    """
    Replaces the old per-user + master daily Excel files written by
    data_logger.DataLogger.log_session(). Same fields, queryable DB instead
    of files that have to be opened in Excel. Still exportable to Excel from
    the Events page.
    """
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, nullable=True)
    camera_name = Column(String, nullable=True)
    date = Column(String, index=True)
    time = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String)
    mask = Column(String)          # "YES" / "NO"
    hat = Column(String)           # "YES" / "NO"
    washing_complete = Column(String)  # "YES" / "NO"
    wash_duration = Column(Integer)
    all_who_steps = Column(String)  # "YES" / "NO"
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AlertLog(Base):
    """Every bot notification sent, so the Alerts page has something to show
    even if the outbound bot call itself fails/is unset."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    camera_name = Column(String, nullable=True)
    message = Column(Text)
    level = Column(String, default="info")  # info | warning | error
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SettingKV(Base):
    """Live-editable behavioural settings (thresholds, wash timers, bot
    credentials) - replaces constants that used to be hardcoded in config.py."""
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(JSON)