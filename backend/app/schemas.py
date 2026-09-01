from typing import Optional, List
from pydantic import BaseModel


class CameraCreate(BaseModel):
    name: str
    source: str  # webcam index as string, or an RTSP/HTTP URL
    room: Optional[str] = None
    enabled: bool = True
    check_mask: bool = True
    check_hat: bool = True
    check_wash: bool = True


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    source: Optional[str] = None
    room: Optional[str] = None
    enabled: Optional[bool] = None
    check_mask: Optional[bool] = None
    check_hat: Optional[bool] = None
    check_wash: Optional[bool] = None
    manual_roi: Optional[List[float]] = None
    sink_y_start: Optional[int] = None


class CameraOut(BaseModel):
    id: int
    name: str
    source: str
    room: Optional[str] = None
    enabled: bool
    check_mask: bool
    check_hat: bool
    check_wash: bool
    manual_roi: Optional[List[float]] = None
    sink_y_start: Optional[int] = None
    connected: bool = False

    class Config:
        from_attributes = True


class EventOut(BaseModel):
    id: int
    camera_id: Optional[int]
    camera_name: Optional[str]
    date: str
    time: str
    first_name: str
    last_name: str
    role: str
    mask: str
    hat: str
    washing_complete: str
    wash_duration: int
    all_who_steps: str

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    camera_name: Optional[str]
    message: str
    level: str
    delivered: bool

    class Config:
        from_attributes = True


class RegisterStaffRequest(BaseModel):
    camera_id: int
    first_name: str
    last_name: str
    role: str = "N/A"


class SettingsUpdate(BaseModel):
    values: dict