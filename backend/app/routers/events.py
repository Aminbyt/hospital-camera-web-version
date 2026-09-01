import io
from typing import Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd

from app.database import get_db
from app.models import Event
from app.schemas import EventOut

router = APIRouter(prefix="/api/events", tags=["events"])


def _apply_filters(q, camera_id, date_from, date_to, user, compliant_only):
    if camera_id is not None:
        q = q.filter(Event.camera_id == camera_id)
    if date_from:
        q = q.filter(Event.date >= date_from)
    if date_to:
        q = q.filter(Event.date <= date_to)
    if user:
        like = f"%{user}%"
        q = q.filter((Event.first_name.ilike(like)) | (Event.last_name.ilike(like)))
    if compliant_only:
        q = q.filter(Event.washing_complete == "YES", Event.mask == "YES", Event.hat == "YES")
    return q


@router.get("", response_model=list[EventOut])
def list_events(
    camera_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: Optional[str] = None,
    compliant_only: bool = False,
    limit: int = Query(200, le=2000),
    db: Session = Depends(get_db),
):
    q = db.query(Event).order_by(Event.id.desc())
    q = _apply_filters(q, camera_id, date_from, date_to, user, compliant_only)
    return q.limit(limit).all()


@router.get("/export")
def export_events(
    camera_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user: Optional[str] = None,
    compliant_only: bool = False,
    db: Session = Depends(get_db),
):
    q = db.query(Event).order_by(Event.id.desc())
    q = _apply_filters(q, camera_id, date_from, date_to, user, compliant_only)
    rows = q.all()

    df = pd.DataFrame([{
        "Date": r.date, "Time": r.time, "Sink": r.camera_name,
        "First Name": r.first_name, "Last Name": r.last_name, "Role": r.role,
        "Mask": r.mask, "Hat": r.hat, "Washing Complete": r.washing_complete,
        "Wash Duration (s)": r.wash_duration, "All WHO Steps": r.all_who_steps,
    } for r in rows])

    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=events_export.xlsx"},
    )
