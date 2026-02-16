from __future__ import annotations

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from app.database.duckdb_data_service import data_service
from app.core.models.database_models import CalendarEntry
from dataclasses import asdict

router = APIRouter(prefix="/calendar", tags=["calendar"])


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

    entries: List[CalendarEntry] = data_service.get_doctor_calendar_for_day(
        doctor_id=doctor_id, day=day
    )

    out: List[dict] = []
    for e in entries:
        if hasattr(e, "to_dict"):
            out.append(e.to_dict())
        else:
            out.append(asdict(e))

    return out


@router.get("/closest-meeting/notes")
def update_closest_meeting_notes(
    doctor_id: int = Query(..., gt=0),
    notes: Optional[str] = Query(default=None),
):
    """
    Updates the closest (or currently running) meeting
    and returns the updated CalendarEntry.
    """

    try:
        updated: CalendarEntry = (
            data_service.update_calendar_entry_notes_of_closest_meeting(
                doctor_id=doctor_id,
                notes=notes,
            )
        )
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if hasattr(updated, "to_dict"):
        return updated.to_dict()

    return asdict(updated)
