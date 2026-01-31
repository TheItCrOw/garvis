from __future__ import annotations

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.database.duckdb_data_service import DataService
from app.core.models.database_models import CalendarEntry
from dataclasses import asdict

router = APIRouter(prefix="/calendar", tags=["calendar"])

ds = DataService()


@router.get("/{doctor_id}", response_model=None)
def get_calendar_of_doctor_for_day(
    doctor_id: int,
    day: Optional[date] = Query(
        default=None,
        description="Day to fetch (YYYY-MM-DD). Defaults to today in service.",
    ),
) -> List[dict]:
    """
    Returns the doctor's calendar entries for a given day.

    Frontend call:
      GET /api/calendar/{doctor_id}?day=YYYY-MM-DD

    Response:
      JSON list of CalendarEntry objects in snake_case keys.
    """
    if doctor_id <= 0:
        raise HTTPException(status_code=400, detail="doctor_id must be positive")

    entries: List[CalendarEntry] = ds.get_doctor_calendar_for_day(
        doctor_id=doctor_id, day=day
    )

    out: List[dict] = []
    for e in entries:
        if hasattr(e, "to_dict"):
            out.append(e.to_dict())
        else:
            out.append(asdict(e))

    return out
