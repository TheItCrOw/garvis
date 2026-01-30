import duckdb
import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Generator, Optional, Any, Dict, List

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

        print(f"Using DuckDB database at: {self.db_path}")
        with self.connection() as con:
            con.execute("SELECT 1").fetchone()

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
                SELECT *
                FROM patient_history
                WHERE patient_id = ?
                ORDER BY event_start_at DESC
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
                SELECT *
                FROM patient_history
                WHERE patient_id = ? AND doctor_id = ?
                ORDER BY event_start_at DESC
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
