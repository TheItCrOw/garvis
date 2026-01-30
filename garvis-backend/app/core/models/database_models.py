from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from typing import Any, Dict, Optional, Type, TypeVar


def _jsonify_value(v: Any) -> Any:
    """Convert non-JSON-native Python types into JSON-safe equivalents."""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


@dataclass(frozen=True, slots=True)
class JsonDataclassMixin:
    """Mixin for dataclasses that need to be safely JSON-serializable."""

    def to_dict(self) -> Dict[str, Any]:
        raw = asdict(self)
        return {k: _jsonify_value(v) for k, v in raw.items()}

    @classmethod
    def from_row(cls: Type["T"], row: Dict[str, Any]) -> "T":
        """
        Create from a dict-like row, e.g. DuckDB fetchdf().to_dict("records")
        or a manual mapping of cursor description -> row tuple.
        """
        return cls(**row)  # type: ignore[arg-type]


T = TypeVar("T", bound=JsonDataclassMixin)


@dataclass(frozen=True, slots=True)
class Patient(JsonDataclassMixin):
    patient_id: int
    created_at: Optional[datetime]

    first_name: Optional[str]
    last_name: Optional[str]
    sex: Optional[str]
    date_of_birth: Optional[date]

    deceased_flag: Optional[bool]
    marital_status: Optional[str]
    language: Optional[str]

    email: Optional[str]
    phone: Optional[str]

    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postal_code: Optional[str]
    country: Optional[str]

    primary_care_provider_id: Optional[int]
    organization_id: Optional[int]
    insurance_plan_id: Optional[int]

    active_flag: Optional[bool]
    last_seen_at: Optional[date]

    height_cm: Optional[float]
    weight_kg: Optional[float]
    bmi: Optional[float]

    smoking_status: Optional[str]
    alcohol_use: Optional[str]
    pregnancy_status: Optional[str]

    has_diabetes: Optional[bool]
    has_hypertension: Optional[bool]
    has_copd: Optional[bool]
    has_ckd: Optional[bool]
    has_asthma: Optional[bool]

    updated_at: Optional[datetime]


@dataclass(frozen=True, slots=True)
class Doctor(JsonDataclassMixin):
    doctor_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    sex: Optional[str]
    specialty: Optional[str]
    years_of_experience: Optional[int]
    email: Optional[str]
    phone: Optional[str]
    age: Optional[int]


@dataclass(frozen=True, slots=True)
class CalendarEntry(JsonDataclassMixin):
    calendar_id: int
    doctor_id: Optional[int]
    patient_id: Optional[int]

    start_at: Optional[datetime]
    end_at: Optional[datetime]

    entry_type: Optional[str]
    title: Optional[str]
    location: Optional[str]
    priority: Optional[str]
    status: Optional[str]
    notes: Optional[str]


@dataclass(frozen=True, slots=True)
class PatientHistory(JsonDataclassMixin):
    history_id: int
    patient_id: Optional[int]
    doctor_id: Optional[int]

    event_type: Optional[str]
    event_start_at: Optional[datetime]
    event_end_at: Optional[datetime]

    chief_complaint: Optional[str]
    diagnosis_summary: Optional[str]
    procedure_performed: Optional[str]
    prescription_given: Optional[str]
    notes: Optional[str]

    outcome: Optional[str]
    follow_up_required: Optional[bool]
    severity: Optional[str]

    created_at: Optional[datetime]
