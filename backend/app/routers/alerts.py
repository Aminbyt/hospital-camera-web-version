from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AlertLog
from app.schemas import AlertOut

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(limit: int = Query(100, le=1000), db: Session = Depends(get_db)):
    return db.query(AlertLog).order_by(AlertLog.id.desc()).limit(limit).all()
