from __future__ import annotations

from datetime import date
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from app.database.duckdb_data_service import DataService
from app.core.models.database_models import CalendarEntry, Patient, PatientHistory
from dataclasses import asdict

router = APIRouter(prefix="/patients", tags=["patients"])

ds = DataService()


@router.get("/{patient_id}", response_model=None)
def get_patient_file(
    patient_id: int,
) -> dict:
    """
    Returns the full information on a patient by its id.

    Frontend call:
      GET /api/patients/{patient_id}

    Response:
      JSON of a patient object in snake_case keys.
    """
    if patient_id <= 0:
        raise HTTPException(status_code=400, detail="patient_id must be positive")

    patient: Patient = ds.get_patient_by_id(patient_id=patient_id)
    return patient.to_dict()


@router.get("/history/{patient_id}", response_model=None)
def get_patient_history(
    patient_id: int,
) -> dict:
    """
    Returns the full history of a patient by its id.

    Frontend call:
      GET /api/patients/history/{patient_id}

    Response:
      JSON of a list of patient histories in snake_case keys.
    """
    if patient_id <= 0:
        raise HTTPException(status_code=400, detail="patient_id must be positive")

    patient_history: list[PatientHistory] = ds.get_patient_history(
        patient_id=patient_id
    )

    out: List[dict] = []
    for e in patient_history:
        if hasattr(e, "to_dict"):
            out.append(e.to_dict())
        else:
            out.append(asdict(e))

    return out
