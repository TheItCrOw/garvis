import base64
import mimetypes
from pathlib import Path
import duckdb
import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Generator, Literal, Optional, Any, Dict, List
from langchain_core.tools import tool
from zoneinfo import ZoneInfo

from app.core.models.database_models import (
    Patient,
    Doctor,
    CalendarEntry,
    PatientHistory,
    JsonDataclassMixin,
)

SERVER_TIME_ZONE = ZoneInfo("America/Los_Angeles")


class DataService:
    def __init__(self, db_path: str = "./data/garvis.duckdb") -> None:
        self.db_path: str = db_path

        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"DuckDB file not found: {self.db_path}")

        with self.connection() as con:
            con.execute("SELECT 1").fetchone()
        print(f"Setup the DataService with DuckDB under {db_path}")

    @contextmanager
    def connection(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Create a new connection per usage, safe for web servers and concurrent requests.
        """
        con: duckdb.DuckDBPyConnection = duckdb.connect(self.db_path, read_only=False)
        try:
            yield con
        finally:
            con.close()

    # ========= Helper methods for free SQL querying =========
    def _fetchone_dict(
        self, con: duckdb.DuckDBPyConnection, sql: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Return one row as {column: value} or None.
        """
        cur = con.execute(sql, params or ())
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def _fetchall_dicts(
        self, con: duckdb.DuckDBPyConnection, sql: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Return all rows as [{column: value}, ...].
        """
        cur = con.execute(sql, params or ())
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in rows]

    def count_patients(self) -> int:
        with self.connection() as con:
            return con.execute("SELECT COUNT(*) FROM patient").fetchone()[0]

    # ========= Specific Task methods =========
    def get_doctor_by_id(self, doctor_id: int) -> Optional["Doctor"]:
        """Query the DuckDB for the available doctors using doctor_id as the parameter"""
        with self.connection() as con:
            row = self._fetchone_dict(
                con,
                """
                SELECT *
                FROM doctor
                WHERE doctor_id = ?
                """,
                (doctor_id,),
            )
            return Doctor.from_row(row) if row else None

    def get_doctor_by_full_name(
        self, first_name: str, last_name: str
    ) -> Optional["Doctor"]:
        """Query the DuckDB for the available doctors using either first name or last name as the parameter"""
        with self.connection() as con:
            row = self._fetchone_dict(
                con,
                """
                SELECT *
                FROM doctor
                WHERE lower(first_name) = lower(?) AND lower(last_name) = lower(?)
                """,
                (first_name, last_name),
            )
            return Doctor.from_row(row) if row else None

    def get_patient_by_id(self, patient_id: int) -> Optional["Patient"]:
        """Query the DuckDB for the patient information using patient_id as the identifier"""
        with self.connection() as con:
            row = self._fetchone_dict(
                con,
                """
                SELECT *
                FROM patient
                WHERE patient_id = ?
                """,
                (patient_id,),
            )
            return Patient.from_row(row) if row else None

    def get_patient_by_full_name(
        self, first_name: str, last_name: str
    ) -> Optional["Patient"]:
        """Query the DuckDB for the patients using either first name or last name as the parameter"""
        with self.connection() as con:
            row = self._fetchone_dict(
                con,
                """
                SELECT *
                FROM patient
                WHERE lower(first_name) = lower(?) AND lower(last_name) = lower(?)
                """,
                (first_name, last_name),
            )
            return Patient.from_row(row) if row else None

    def get_doctor_calendar_for_day(
        self, doctor_id: int, day: Optional[date] = None
    ) -> List["CalendarEntry"]:
        """
        Full calendar (all entries) for a doctor on a given day.
        Default day: today in Europe/Berlin.
        """
        if day is None:
            day = datetime.now(SERVER_TIME_ZONE).date()

        with self.connection() as con:
            rows = self._fetchall_dicts(
                con,
                """
                SELECT *
                FROM calendar
                WHERE doctor_id = ? AND DATE(start_at) = ?
                ORDER BY start_at ASC
                """,
                (doctor_id, day),
            )
            return [CalendarEntry.from_row(r) for r in rows]

    def get_patient_history(self, patient_id: int) -> List["PatientHistory"]:
        with self.connection() as con:
            rows = self._fetchall_dicts(
                con,
                """
                SELECT
                ph.*,
                x.xray_id AS xray_img_id
                FROM patient_history ph
                LEFT JOIN xray x
                ON x.history_id = ph.history_id
                WHERE ph.patient_id = ?
                ORDER BY ph.event_start_at DESC
                """,
                (patient_id,),
            )
            return [PatientHistory.from_row(r) for r in rows]

    def get_patient_history_with_doctor(
        self, patient_id: int, doctor_id: int
    ) -> List["PatientHistory"]:
        with self.connection() as con:
            rows = self._fetchall_dicts(
                con,
                """
                SELECT
                ph.*,
                x.xray_id AS xray_img_id
                FROM patient_history ph
                LEFT JOIN xray x
                ON x.history_id = ph.history_id
                WHERE ph.patient_id = ? AND ph.doctor_id = ?
                ORDER BY ph.event_start_at DESC
                """,
                (patient_id, doctor_id),
            )
            return [PatientHistory.from_row(r) for r in rows]

    def get_patient_with_full_history(
        self, patient_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Returns a JSON-friendly bundle:
        {
          "patient": Patient,
          "history": [PatientHistory, ...]
        }
        """
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            return None

        history = self.get_patient_history(patient_id)
        return {"patient": patient, "history": history}

    def get_xray_by_id(self, xray_id: int) -> Optional[Dict[str, Any]]:
        """
        #TODO: Brando, you can probably use this as an Agent Tool.
        Returns the xray row as is in the DuckDB with the path to the actual image.
        """
        with self.connection() as con:
            rows = self._fetchall_dicts(
                con,
                """
                SELECT *
                FROM xray
                WHERE xray_id = ?
                """,
                (xray_id,),
            )
            return rows[0] if rows else None

    def get_all_xrays_of_patient(self, patient_id: int) -> List[Dict[str, Any]]:
        """
        Returns xray table rows for the patient (metadata only, includes file_path).
        """
        with self.connection() as con:
            return self._fetchall_dicts(
                con,
                """
                SELECT *
                FROM xray
                WHERE patient_id = ?
                ORDER BY acquired_at DESC, xray_id DESC
                """,
                (patient_id,),
            )

    def load_xray_image_bytes(self, xray_id: int) -> tuple[bytes, str]:
        """
        Given an xray_id, returns the bytes of the actual xray image.
        Returns (bytes, mime).
        """
        xray = self.get_xray_by_id(xray_id)
        if not xray:
            raise KeyError(f"Unknown xray_id={xray_id}")

        path = Path(xray["file_path"])

        # For safety: ensure path stays inside my allowed base dir
        base_dir = Path("data/xrays").resolve()
        resolved = path.resolve()
        if base_dir not in resolved.parents:
            raise PermissionError("Invalid file path")

        data = path.read_bytes()
        mime, _ = mimetypes.guess_type(str(path))
        return data, (mime or "application/octet-stream")

    def load_xray_image_as_base64(
        self,
        xray_id: int,
        *,
        as_data_url: bool = False,
    ) -> tuple[str, str]:
        """
        #TODO: Brando, you can probably use this as an Agent Tool.
        Based on a xray id, returns (base64_string, mime) where base64_string is the encoded xray image.
        If as_data_url=True, base64_string is a full data URL usable directly in <img src="...">.
        """
        data, mime = self.load_xray_image_bytes(xray_id)
        b64 = base64.b64encode(data).decode("ascii")

        if as_data_url:
            return (f"data:{mime};base64,{b64}", mime)

        return (b64, mime)

    def load_all_xray_images_of_patient_as_bytes(
        self,
        patient_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of:
        { "xray_id": int, "mime": str, "bytes": bytes }
        """
        xrays = self.get_all_xrays_of_patient(patient_id)

        out: List[Dict[str, Any]] = []
        for x in xrays:
            xray_id = int(x["xray_id"])
            data, mime = self.load_xray_image_bytes(xray_id)
            out.append({"xray_id": xray_id, "mime": mime, "bytes": data})

        return out

    def load_all_xray_images_of_patient_as_base64(
        self,
        patient_id: int,
        *,
        as_data_url: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        #TODO: Brando, you can probably use this as an Agent Tool.
        Returns a list of xray ids alongside their actual xray images encoded in base64:
        { "xray_id": int, "mime": str, "base64": str }
        If as_data_url=True, 'base64' will actually be a full data URL usable in <img src="...">.
        """
        xrays = self.get_all_xrays_of_patient(patient_id)

        out: List[Dict[str, Any]] = []
        for x in xrays:
            xray_id = int(x["xray_id"])
            b64, mime = self.load_xray_image_as_base64(xray_id, as_data_url=as_data_url)
            out.append({"xray_id": xray_id, "mime": mime, "base64": b64})

        return out

    def add_calendar_entry(
        self,
        doctor_id: int,
        patient_id: int,
        start_at: datetime,
        end_at: datetime,
        entry_type: Literal[
            "consultation",
            "emergency",
            "surgery",
            "prescription",
            "follow_up",
            "hospitalization",
            "referral",
        ],
        title: str,
        location: Optional[
            Literal[
                "Clinic Room 1",
                "Clinic Room 2",
                "Clinic Room 3",
                "Radiology",
                "OR 1",
                "OR 2",
                "Online",
                "Conference Room",
            ]
        ] = None,
        priority: str = "normal",
        status: str = "scheduled",
        notes: Optional[str] = None,
    ) -> "CalendarEntry":
        """
        Add a calendar entry for a doctor with a patient.
        Returns the created CalendarEntry row.
        """
        with self.connection() as con:
            row = self._fetchone_dict(
                con,
                """
                INSERT INTO calendar (
                    doctor_id, patient_id, start_at, end_at,
                    entry_type, title, location, priority, status, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING
                    calendar_id, doctor_id, patient_id, start_at, end_at,
                    entry_type, title, location, priority, status, notes
                """,
                (
                    doctor_id,
                    patient_id,
                    start_at,
                    end_at,
                    entry_type,
                    title,
                    location,
                    priority,
                    status,
                    notes,
                ),
            )
            if not row:
                raise RuntimeError("Insert into calendar did not return a row.")
            return CalendarEntry.from_row(row)

    def add_patient_history(
        self,
        patient_id: int,
        doctor_id: int,
        event_type: str,
        event_start_at: datetime,
        event_end_at: Optional[datetime] = None,
        chief_complaint: Optional[str] = None,
        diagnosis_summary: Optional[str] = None,
        procedure_performed: Optional[str] = None,
        prescription_given: Optional[str] = None,
        notes: Optional[str] = None,
        outcome: Optional[str] = None,
        follow_up_required: Optional[bool] = None,
        severity: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> "PatientHistory":
        """
        Add a new patient history event.
        Returns the created PatientHistory row.
        """
        if created_at is None:
            created_at = datetime.now(SERVER_TIME_ZONE)

        with self.connection() as con:
            row = self._fetchone_dict(
                con,
                """
                INSERT INTO patient_history (
                    patient_id, doctor_id, event_type,
                    event_start_at, event_end_at,
                    chief_complaint, diagnosis_summary, procedure_performed,
                    prescription_given, notes, outcome, follow_up_required,
                    severity, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING
                    history_id, patient_id, doctor_id, event_type,
                    event_start_at, event_end_at,
                    chief_complaint, diagnosis_summary, procedure_performed,
                    prescription_given, notes, outcome, follow_up_required,
                    severity, created_at
                """,
                (
                    patient_id,
                    doctor_id,
                    event_type,
                    event_start_at,
                    event_end_at,
                    chief_complaint,
                    diagnosis_summary,
                    procedure_performed,
                    prescription_given,
                    notes,
                    outcome,
                    follow_up_required,
                    severity,
                    created_at,
                ),
            )
            if not row:
                raise RuntimeError("Insert into patient_history did not return a row.")
            return PatientHistory.from_row(row)

    def prescribe_medication(
        self,
        patient_id: int,
        doctor_id: int,
        medication: str,
        *,
        event_start_at: Optional[datetime] = None,
        event_end_at: Optional[datetime] = None,
        diagnosis_summary: Optional[str] = None,
        chief_complaint: Optional[str] = None,
        notes: Optional[str] = None,
        severity: Optional[str] = None,
        follow_up_required: Optional[bool] = True,
        outcome: Optional[str] = None,
    ) -> "PatientHistory":
        """
        Prescribe a medication to a patient.
        This is modeled as creating a patient_history entry
        with prescription_given filled.
        """
        if event_start_at is None:
            event_start_at = datetime.now(SERVER_TIME_ZONE)

        # If no end time provided, leave NULL (or set same as start if you prefer)
        return self.add_patient_history(
            patient_id=patient_id,
            doctor_id=doctor_id,
            event_type="prescription",
            event_start_at=event_start_at,
            event_end_at=event_end_at,
            chief_complaint=chief_complaint,
            diagnosis_summary=diagnosis_summary,
            prescription_given=medication,
            notes=notes,
            outcome=outcome,
            follow_up_required=follow_up_required,
            severity=severity,
        )

    def update_patient_address(
        self,
        patient_id: int,
        *,
        address_line1: Optional[str] = None,
        address_line2: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: Optional[str] = None,
    ) -> Optional["Patient"]:
        """
        Update patient address fields. Only updates the fields you pass (non-None).
        Also updates updated_at to now.

        Returns the updated Patient or None if patient_id not found.
        """
        fields: List[str] = []
        params: List[Any] = []

        def add(field: str, value: Any) -> None:
            fields.append(f"{field} = ?")
            params.append(value)

        if address_line1 is not None:
            add("address_line1", address_line1)
        if address_line2 is not None:
            add("address_line2", address_line2)
        if city is not None:
            add("city", city)
        if state is not None:
            add("state", state)
        if postal_code is not None:
            add("postal_code", postal_code)
        if country is not None:
            add("country", country)

        add("updated_at", datetime.now(SERVER_TIME_ZONE))

        if not fields:
            return self.get_patient_by_id(patient_id)

        sql = f"""
            UPDATE patient
            SET {", ".join(fields)}
            WHERE patient_id = ?
            RETURNING
                patient_id, created_at, first_name, last_name, sex, date_of_birth,
                deceased_flag, marital_status, language, email, phone,
                address_line1, address_line2, city, state, postal_code, country,
                primary_care_provider_id, organization_id, insurance_plan_id,
                active_flag, last_seen_at, height_cm, weight_kg, bmi,
                smoking_status, alcohol_use, pregnancy_status,
                has_diabetes, has_hypertension, has_copd, has_ckd, has_asthma,
                updated_at
        """

        params.append(patient_id)

        with self.connection() as con:
            row = self._fetchone_dict(con, sql, tuple(params))
            return Patient.from_row(row) if row else None

    # TOOOOOOO...OOOOOOOOLS

    def return_tools(self):
        @tool
        def doctor_by_id(doctor_id: int) -> Optional["Doctor"]:
            """Query the DuckDB for the available doctors using doctor_id as the parameter.
            Only query this table when explicitly instructed."""
            return self.get_doctor_by_id(doctor_id)

        @tool
        def doctor_by_full_name(first_name: str, last_name: str) -> Optional["Doctor"]:
            """Query the DuckDB for the available doctors using doctor_id as the parameter.
            Only query this table when explicitly instructed."""
            return self.get_doctor_by_full_name(first_name, last_name)

        @tool
        def patient_by_id(patient_id: int) -> Optional["Patient"]:
            """Query the DuckDB for the patient information using patient_id as the parameter.
            Only query this table when explicitly instructed."""
            return self.get_patient_by_id(patient_id)

        @tool
        def patient_by_full_name(
            first_name: str, last_name: str
        ) -> Optional["Patient"]:
            """Query the DuckDB for the patients using first name and last name as the parameters.
            Only query this table when explicitly instructed."""
            return self.get_patient_by_full_name(first_name, last_name)

        @tool
        def doctor_calendar_for_day(
            doctor_id: int, day: Optional[date] = None
        ) -> List["CalendarEntry"]:
            """Query the DuckDB for the calendar and scheduled activities of a doctor using doctor_id and with an optional date parameters.
             Full calendar (all entries) for a doctor on a given day.
             Default day: today in Europe/Berlin.
            Only query this table when explicitly instructed."""
            return self.get_doctor_calendar_for_day(doctor_id, day)

        @tool
        def patient_history(patient_id: int) -> List["PatientHistory"]:
            """Query the DuckDB for a specific patient's history using the patient_id as parameter.
            Only query this table when explicitly instructed."""
            return self.get_patient_history(patient_id)

        @tool
        def patient_history_with_doctor(
            patient_id: int, doctor_id: int
        ) -> List["PatientHistory"]:
            """Query the DuckDB for a specific patient's history with a doctor using the patient_id and doctor_id as parameters.
            Only query this table when explicitly instructed."""
            return self.get_patient_history_with_doctor(patient_id, doctor_id)

        @tool
        def patient_with_full_history(patient_id: int) -> Optional[Dict[str, Any]]:
            """Query the DuckDB for a specific patient's history using the patient_id.
            Only query this table when explicitly instructed."""
            return self.get_patient_with_full_history(patient_id)

        @tool
        def tool_add_calendar_entry(
            doctor_id: int,
            patient_id: int,
            start_at: datetime,
            end_at: datetime,
            entry_type: Literal[
                "consultation",
                "emergency",
                "surgery",
                "prescription",
                "follow_up",
                "hospitalization",
                "referral",
            ],
            title: str,
            location: Optional[
                Literal[
                    "Clinic Room 1",
                    "Clinic Room 2",
                    "Clinic Room 3",
                    "Radiology",
                    "OR 1",
                    "OR 2",
                    "Online",
                    "Conference Room",
                ]
            ] = None,
            priority: str = "normal",
            status: str = "scheduled",
            notes: Optional[str] = None,
        ) -> "CalendarEntry":
            """
            Add a calendar entry for a doctor with a patient.
            Ensure that the required fields have values and confirm them from the user before adding.
            Returns the created CalendarEntry row. Only invoke this tool if the intent is clear
            """

            return self.add_calendar_entry(
                doctor_id=doctor_id,
                patient_id=patient_id,
                start_at=start_at,
                end_at=end_at,
                entry_type=entry_type,
                title=title,
                location=location,
                priority=priority,
                status=status,
                notes=notes,
            )

        @tool
        def tool_add_patient_history(
            patient_id: int,
            doctor_id: int,
            event_type: str,
            event_start_at: datetime,
            event_end_at: Optional[datetime] = None,
            chief_complaint: Optional[str] = None,
            diagnosis_summary: Optional[str] = None,
            procedure_performed: Optional[str] = None,
            prescription_given: Optional[str] = None,
            notes: Optional[str] = None,
            outcome: Optional[str] = None,
            follow_up_required: Optional[bool] = None,
            severity: Optional[str] = None,
            created_at: Optional[datetime] = None,
        ) -> "PatientHistory":
            """
            Add a new patient history event.
            Ensure that the required fields have values and confirm them from the user before adding.
            Returns the created PatientHistory row. Only invoke this tool if the intent is clear
            """
            return self.add_patient_history(
                patient_id=patient_id,
                doctor_id=doctor_id,
                event_type=event_type,
                event_start_at=event_start_at,
                event_end_at=event_end_at,
                chief_complaint=chief_complaint,
                diagnosis_summary=diagnosis_summary,
                procedure_performed=procedure_performed,
                prescription_given=prescription_given,
                notes=notes,
                outcome=outcome,
                follow_up_required=follow_up_required,
                severity=severity,
                created_at=created_at,
            )

        @tool
        def tool_update_patient_address(
            patient_id: int,
            address_line1: Optional[str] = None,
            address_line2: Optional[str] = None,
            city: Optional[str] = None,
            state: Optional[str] = None,
            postal_code: Optional[str] = None,
            country: Optional[str] = None,
        ) -> Optional["Patient"]:
            """
            Update patient address fields. Only updates the fields you pass (non-None).
            Also updates updated_at to now.
            Returns the updated Patient or None if patient_id not found.
            """

            self.update_patient_address(
                patient_id=patient_id,
                address_line1=address_line1,
                address_line2=address_line2,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
            )

        @tool
        def tool_prescribe_medication(
            patient_id: int,
            doctor_id: int,
            medication: str,
            event_start_at: Optional[datetime] = None,
            event_end_at: Optional[datetime] = None,
            diagnosis_summary: Optional[str] = None,
            chief_complaint: Optional[str] = None,
            notes: Optional[str] = None,
            severity: Optional[str] = None,
            follow_up_required: Optional[bool] = True,
            outcome: Optional[str] = None,
        ) -> "PatientHistory":
            """
            Prescribe a medication to a patient.
            This is modeled as creating a patient_history entry
            with prescription_given filled.
            """

            return self.prescribe_medication(
                patient_id=patient_id,
                doctor_id=doctor_id,
                medication=medication,
                event_start_at=event_start_at,
                event_end_at=event_end_at,
                diagnosis_summary=diagnosis_summary,
                chief_complaint=chief_complaint,
                notes=notes,
                severity=severity,
                follow_up_required=follow_up_required,
                outcome=outcome,
            )

        # return the tools
        return [
            doctor_by_id,
            doctor_by_full_name,
            patient_by_id,
            patient_by_full_name,
            doctor_calendar_for_day,
            patient_history,
            patient_history_with_doctor,
            patient_with_full_history,
            tool_add_calendar_entry,
            tool_add_patient_history,
            tool_update_patient_address,
            tool_prescribe_medication,
        ]


data_service = DataService()
