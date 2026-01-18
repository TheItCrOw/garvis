"""
Script for generating the synthetic, randomized healthcare dataset.
We use the faker package for that.
"""

from __future__ import annotations

import duckdb
import numpy as np
import os
import pandas as pd

from datetime import date, timedelta
from faker import Faker
from pathlib import Path


SEED = 42
OUTPUT_PATH = "./data/tables"
rng = np.random.default_rng(SEED)
faker = Faker()
faker.seed_instance(SEED)


# ===== Helpers =====
def random_date(start: date, end: date, size: int) -> pd.Series:
    """Generate random dates between start and end (inclusive) as a pandas Series."""
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    delta_days = (end_ts - start_ts).days

    dates = start_ts + pd.to_timedelta(
        rng.integers(0, delta_days + 1, size=size), unit="D"
    )
    return pd.Series(dates)


def maybe_null(values, p_null: float):
    """Randomly set values to NA with probability p_null (handles ndarray/Series/Index)."""
    arr = np.asarray(values, dtype=object)
    mask = rng.random(arr.shape[0]) < p_null
    arr[mask] = None
    return arr


def _normalize_probs(p):
    p = np.array(p, dtype=float)
    p = np.clip(p, 0, None)
    s = p.sum()
    if s == 0:
        # fallback uniform
        return np.ones_like(p) / len(p)
    return p / s


def save_to_duckdb(db_path: str, tables: dict[str, "pd.DataFrame"]) -> None:
    """
    Persist pandas DataFrames into a DuckDB database file.
    """
    con = duckdb.connect(db_path)

    try:
        con.execute("PRAGMA threads=4;")

        for name, df in tables.items():
            # Register the DF as a DuckDB view, then materialize it as a table
            con.register("df_view", df)
            con.execute(f"DROP TABLE IF EXISTS {name}")
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM df_view")
            con.unregister("df_view")

        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_patient_patient_id ON patient(patient_id)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_doctor_doctor_id ON doctor(doctor_id)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_hist_patient_id ON patient_history(patient_id)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_hist_doctor_id ON patient_history(doctor_id)"
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_xray_hist_id ON xray(history_id)")
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_cal_doctor_id ON calendar(doctor_id)"
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_cal_patient_id ON calendar(patient_id)"
        )

    finally:
        con.close()


# ===== Faker tables generation. They all return a pandas dataframe. =====
# ===== Patient Table
def generate_patient_table(n_patients: int) -> pd.DataFrame:
    """
    Generates a dataframe containing synthetic data of patient rows.
    """
    today = date.today()

    patient_id = np.arange(1, n_patients + 1, dtype=np.int64)

    date_of_birth = random_date(
        start=date(1920, 1, 1), end=date(2020, 12, 31), size=n_patients
    )

    # death (rare, after birth)
    deceased_flag = rng.random(n_patients) < 0.08

    height_cm = rng.normal(170, 10, n_patients).clip(140, 210)
    weight_kg = rng.normal(75, 15, n_patients).clip(40, 180)
    bmi = weight_kg / ((height_cm / 100) ** 2)

    df = pd.DataFrame(
        {
            # identifiers
            "patient_id": patient_id,
            "created_at": pd.Timestamp.utcnow(),
            # demographics
            "first_name": [faker.first_name() for _ in range(n_patients)],
            "last_name": [faker.last_name() for _ in range(n_patients)],
            "sex": rng.choice(
                ["female", "male", "intersex", "unknown"],
                p=[0.49, 0.49, 0.01, 0.01],
                size=n_patients,
            ),
            "date_of_birth": date_of_birth,
            "deceased_flag": deceased_flag,
            "marital_status": maybe_null(
                rng.choice(
                    ["single", "married", "divorced", "widowed"], size=n_patients
                ),
                p_null=0.15,
            ),
            "language": maybe_null(
                rng.choice(["English", "German", "Spanish", "French"], size=n_patients),
                p_null=0.2,
            ),
            # contact & address
            "email": maybe_null(
                np.array([faker.email() for _ in range(n_patients)]), p_null=0.25
            ),
            "phone": maybe_null(
                np.array([faker.phone_number() for _ in range(n_patients)]), p_null=0.2
            ),
            "address_line1": maybe_null(
                np.array([faker.street_address() for _ in range(n_patients)]),
                p_null=0.1,
            ),
            "address_line2": maybe_null(
                np.array([faker.secondary_address() for _ in range(n_patients)]),
                p_null=0.8,
            ),
            "city": maybe_null(
                np.array([faker.city() for _ in range(n_patients)]), p_null=0.1
            ),
            "state": maybe_null(
                np.array([faker.state() for _ in range(n_patients)]), p_null=0.1
            ),
            "postal_code": maybe_null(
                np.array([faker.postcode() for _ in range(n_patients)]), p_null=0.1
            ),
            "country": "USA",
            # healthcare administrative (FK placeholders)
            "primary_care_provider_id": maybe_null(
                rng.integers(1, 5000, size=n_patients), p_null=0.3
            ),
            "organization_id": maybe_null(
                rng.integers(1, 500, size=n_patients), p_null=0.2
            ),
            "insurance_plan_id": maybe_null(
                rng.integers(1, 200, size=n_patients), p_null=0.15
            ),
            "active_flag": ~deceased_flag,
            "last_seen_at": maybe_null(
                random_date(start=date(2015, 1, 1), end=today, size=n_patients),
                p_null=0.25,
            ),
            # clinical basics
            "height_cm": np.round(height_cm, 2),
            "weight_kg": np.round(weight_kg, 2),
            "bmi": np.round(bmi, 2),
            "smoking_status": maybe_null(
                rng.choice(
                    ["never", "former", "current"],
                    p=[0.55, 0.25, 0.20],
                    size=n_patients,
                ),
                p_null=0.1,
            ),
            "alcohol_use": maybe_null(
                rng.choice(
                    ["none", "social", "daily"], p=[0.3, 0.5, 0.2], size=n_patients
                ),
                p_null=0.15,
            ),
            "pregnancy_status": maybe_null(
                rng.choice(["pregnant", "not_pregnant"], size=n_patients), p_null=0.85
            ),
            # high-level conditions
            "has_diabetes": rng.random(n_patients) < 0.12,
            "has_hypertension": rng.random(n_patients) < 0.25,
            "has_copd": rng.random(n_patients) < 0.05,
            "has_ckd": rng.random(n_patients) < 0.04,
            "has_asthma": rng.random(n_patients) < 0.08,
            # governance
            "updated_at": pd.Timestamp.utcnow(),
        }
    )

    return df


# ===== Doctors Table
def generate_doctor_table(n_doctors: int) -> pd.DataFrame:
    """
    Generates a dataframe containing synthetic data of doctor rows.
    """
    doctor_id = np.arange(1, n_doctors + 1, dtype=np.int64)

    age = rng.integers(28, 70, size=n_doctors)
    years_of_experience = np.clip(age - rng.integers(25, 35, size=n_doctors), 0, None)

    df = pd.DataFrame(
        {
            "doctor_id": doctor_id,
            "first_name": [faker.first_name() for _ in range(n_doctors)],
            "last_name": [faker.last_name() for _ in range(n_doctors)],
            "sex": rng.choice(
                ["female", "male", "intersex", "unknown"],
                p=[0.48, 0.48, 0.02, 0.02],
                size=n_doctors,
            ),
            "specialty": rng.choice(
                [
                    "internal_medicine",
                    "cardiology",
                    "neurology",
                    "orthopedics",
                    "general_practice",
                    "dermatology",
                    "psychiatry",
                    "pediatrics",
                ],
                size=n_doctors,
            ),
            "years_of_experience": years_of_experience.astype(int),
            "email": [faker.unique.email() for _ in range(n_doctors)],
            "phone": [faker.phone_number() for _ in range(n_doctors)],
            "age": age.astype(int),
        }
    )

    return df


# ===== Patient History Table
def generate_patient_history_table(
    patient_df: pd.DataFrame,
    doctors_df: pd.DataFrame,
    n_events: int,
) -> pd.DataFrame:
    """
    Generate a synthetic patient_history / encounters table.

    Foreign keys:
      - patient_id sampled from patient_df["patient_id"]
      - doctor_id sampled from doctors_df["doctor_id"]

    Notes are bullet-style text.
    """
    patient_ids = patient_df["patient_id"].to_numpy(dtype=np.int64)
    doctor_ids = doctors_df["doctor_id"].to_numpy(dtype=np.int64)

    # Event types (includes your 4 + some common extras)
    event_types = np.array(
        [
            "consultation",
            "emergency",
            "surgery",
            "prescription",
            "follow_up",
            "hospitalization",
            "diagnostic_test",
            "vaccination",
            "referral",
        ]
    )
    event_probs = np.array([0.40, 0.10, 0.06, 0.14, 0.12, 0.06, 0.07, 0.03, 0.02])
    event_probs = event_probs / event_probs.sum()

    severity_levels = np.array(["low", "moderate", "high", "critical"])
    severity_probs = np.array([0.55, 0.30, 0.12, 0.03])

    outcomes = np.array(["resolved", "ongoing", "admitted", "referred"])
    outcome_probs = np.array([0.62, 0.18, 0.15, 0.05])

    # Simple vocab pools for synthetic clinical text
    complaints = np.array(
        [
            "abdominal pain",
            "chest pain",
            "headache",
            "shortness of breath",
            "fever",
            "back pain",
            "dizziness",
            "nausea",
            "rash",
            "joint pain",
            "fatigue",
            "cough",
            "sore throat",
            "urinary pain",
            "palpitations",
        ]
    )

    diagnoses = np.array(
        [
            "viral infection",
            "gastroenteritis",
            "hypertension",
            "migraine",
            "anxiety",
            "asthma exacerbation",
            "urinary tract infection",
            "muscle strain",
            "dermatitis",
            "type 2 diabetes (suspected)",
            "pneumonia (suspected)",
            "acute coronary syndrome (rule out)",
        ]
    )

    procedures = np.array(
        [
            "ECG",
            "blood test panel",
            "X-ray",
            "ultrasound",
            "CT scan",
            "wound care",
            "suturing",
            "IV fluids",
            "appendectomy",
            "arthroscopy",
            "biopsy",
            "vaccination",
        ]
    )

    prescriptions = np.array(
        [
            "ibuprofen",
            "paracetamol",
            "amoxicillin",
            "azithromycin",
            "omeprazole",
            "metformin",
            "salbutamol inhaler",
            "prednisone",
            "lisinopril",
            "atorvastatin",
            "ondansetron",
        ]
    )

    # Sample foreign keys + types
    history_id = np.arange(1, n_events + 1, dtype=np.int64)
    patient_id = rng.choice(patient_ids, size=n_events, replace=True)
    doctor_id = rng.choice(doctor_ids, size=n_events, replace=True)

    event_type = rng.choice(event_types, p=event_probs, size=n_events, replace=True)
    severity = rng.choice(
        severity_levels, p=severity_probs, size=n_events, replace=True
    )
    outcome = rng.choice(outcomes, p=outcome_probs, size=n_events, replace=True)
    follow_up_required = rng.random(n_events) < 0.28

    # Event timing
    now = pd.Timestamp.now(tz=None)
    start_offsets_days = rng.integers(0, 365 * 8, size=n_events)
    event_start_at = (
        now
        - pd.to_timedelta(start_offsets_days, unit="D")
        - pd.to_timedelta(rng.integers(0, 24 * 60, size=n_events), unit="m")
    )

    # Durations depend on event_type
    duration_minutes = np.empty(n_events, dtype=np.int64)
    for i, et in enumerate(event_type):
        if et in (
            "consultation",
            "follow_up",
            "prescription",
            "vaccination",
            "referral",
        ):
            duration_minutes[i] = int(rng.integers(10, 45))
        elif et in ("emergency", "diagnostic_test"):
            duration_minutes[i] = int(rng.integers(60, 6 * 60))
        elif et == "surgery":
            duration_minutes[i] = int(rng.integers(60, 6 * 60))
        elif et == "hospitalization":
            duration_minutes[i] = int(rng.integers(8 * 60, 5 * 24 * 60))  # 8h to 5d
        else:
            duration_minutes[i] = int(rng.integers(15, 90))

    event_end_at = event_start_at + pd.to_timedelta(duration_minutes, unit="m")

    # Clinical fields (short + nullable depending on type)
    chief_complaint = rng.choice(complaints, size=n_events, replace=True)
    diagnosis_summary = rng.choice(diagnoses, size=n_events, replace=True)

    procedure_performed = np.array([None] * n_events, dtype=object)
    prescription_given = np.array([None] * n_events, dtype=object)

    for i, et in enumerate(event_type):
        if et in ("diagnostic_test", "surgery", "emergency", "hospitalization"):
            procedure_performed[i] = str(rng.choice(procedures))
        if et in (
            "prescription",
            "consultation",
            "emergency",
            "follow_up",
            "hospitalization",
        ):
            # sometimes multiple meds
            if rng.random() < 0.20:
                meds = rng.choice(prescriptions, size=2, replace=False)
                prescription_given[i] = f"{meds[0]}; {meds[1]}"
            else:
                prescription_given[i] = str(rng.choice(prescriptions))

    # Notes (bulletpoints)
    def make_notes(et: str, comp: str, diag: str, proc, rx, sev: str, fu: bool) -> str:
        bullets = []
        bullets.append(f"- Chief complaint: {comp}.")
        # Add a short, synthetic "assessment"
        bullets.append(f"- Assessment: {diag}. Severity: {sev}.")
        if (
            et in ("diagnostic_test", "emergency", "hospitalization")
            and proc is not None
        ):
            bullets.append(f"- Performed: {proc}.")
        if et == "surgery" and proc is not None:
            bullets.append(f"- Procedure: {proc}. No complications noted.")
        if rx is not None:
            bullets.append(f"- Prescribed: {rx}.")
        if et == "referral":
            bullets.append(
                "- Referred to specialist; patient informed about next steps."
            )
        if fu:
            bullets.append("- Follow-up recommended within 1–2 weeks.")
        else:
            bullets.append("- No follow-up required unless symptoms worsen.")
        # Optional extra line to make notes feel clinical
        if rng.random() < 0.35:
            bullets.append(
                f"- Patient education provided; return precautions discussed."
            )
        return "\n".join(bullets)

    notes = [
        make_notes(
            et=str(event_type[i]),
            comp=str(chief_complaint[i]),
            diag=str(diagnosis_summary[i]),
            proc=procedure_performed[i],
            rx=prescription_given[i],
            sev=str(severity[i]),
            fu=bool(follow_up_required[i]),
        )
        for i in range(n_events)
    ]

    df = pd.DataFrame(
        {
            "history_id": history_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "event_type": event_type,
            "event_start_at": pd.to_datetime(event_start_at),
            "event_end_at": pd.to_datetime(event_end_at),
            "chief_complaint": chief_complaint,
            "diagnosis_summary": diagnosis_summary,
            "procedure_performed": procedure_performed,
            "prescription_given": prescription_given,
            "notes": notes,
            "outcome": outcome,
            "follow_up_required": follow_up_required,
            "severity": severity,
            "created_at": pd.Timestamp.utcnow(),
        }
    )

    return df


# ===== XRays
def index_xray_files(base_dir: str = "./data/xrays") -> pd.DataFrame:
    """
    We have some xrays in the repo under ./data/xrays which we will link to
    patients and their history.

    Expects:
      ./data/xrays/normal/*.jpeg
      ./data/xrays/pneumonia/*.jpeg

    Returns a DataFrame with:
      - file_path (relative path)
      - image_label ('normal'|'pneumonia')
      - file_name
      - ext
    """
    base = Path(base_dir)
    rows = []

    for label in ("normal", "pneumonia"):
        folder = base / label
        if not folder.exists():
            continue

        for p in folder.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                rows.append(
                    {
                        "file_path": str(
                            p.as_posix()
                        ),  # keep as relative-ish path you can store in SQL
                        "image_label": label,
                        "file_name": p.name,
                        "ext": p.suffix.lower(),
                    }
                )

    df = pd.DataFrame(rows)
    if df.empty:
        raise FileNotFoundError(
            f"No xray image files found under {base_dir}. "
            f"Expected folders: {base_dir}/normal and {base_dir}/pneumonia"
        )

    # stable order for reproducible sampling
    df = df.sort_values(["image_label", "file_name"], kind="stable").reset_index(
        drop=True
    )
    return df


def generate_xray_study_table(
    patient_history_df: pd.DataFrame,
    xray_index_df: pd.DataFrame,
    *,
    max_images_per_event: int = 1,
    attach_prob_by_type: dict | None = None,
    respiratory_keywords: tuple[str, ...] = (
        "cough",
        "shortness of breath",
        "fever",
        "pneumonia",
        "dyspnea",
    ),
    label_noise_prob: float = 0.08,
) -> pd.DataFrame:
    """
    Creates an imaging table with FKs to:
      - patient_history_df.history_id
      - patient_history_df.patient_id

    Strategy:
      - Choose candidate events (by event_type; weighted attach probabilities)
      - Prefer respiratory-related events (based on complaint/diagnosis text)
      - Assign label:
          pneumonia if diagnosis suggests pneumonia (else normal),
          with some label_noise_prob to avoid being perfectly separable
    """
    required = {
        "history_id",
        "patient_id",
        "event_type",
        "event_start_at",
        "event_end_at",
        "chief_complaint",
        "diagnosis_summary",
    }
    missing = required - set(patient_history_df.columns)
    if missing:
        raise ValueError(
            f"patient_history_df missing required columns: {sorted(missing)}"
        )

    if attach_prob_by_type is None:
        attach_prob_by_type = {
            "emergency": 0.40,
            "hospitalization": 0.55,
            "diagnostic_test": 0.75,
            "consultation": 0.10,
            "follow_up": 0.08,
            "referral": 0.06,
            "surgery": 0.02,
            "prescription": 0.03,
            "vaccination": 0.01,
        }

    # Make sure we can draw from both labels (or at least one)
    x_norm = xray_index_df.loc[
        xray_index_df["image_label"] == "normal", "file_path"
    ].to_numpy()
    x_pneu = xray_index_df.loc[
        xray_index_df["image_label"] == "pneumonia", "file_path"
    ].to_numpy()
    if len(x_norm) == 0 and len(x_pneu) == 0:
        raise ValueError("xray_index_df has no rows.")
    if len(x_norm) == 0 or len(x_pneu) == 0:
        # still works, but label assignment will be forced
        pass

    # Normalize / coerce timestamps
    ph = patient_history_df.copy()
    ph["event_start_at"] = pd.to_datetime(ph["event_start_at"])
    ph["event_end_at"] = pd.to_datetime(ph["event_end_at"], errors="coerce")

    # Respiratory relevance score (boolean)
    cc = ph["chief_complaint"].fillna("").str.lower()
    dx = ph["diagnosis_summary"].fillna("").str.lower()
    respiratory_hit = pd.Series(False, index=ph.index)

    for kw in respiratory_keywords:
        respiratory_hit |= cc.str.contains(kw, na=False) | dx.str.contains(kw, na=False)

    # Candidate selection: event_type-based probability, boosted if respiratory-related
    et = ph["event_type"].fillna("").astype(str)
    base_prob = et.map(attach_prob_by_type).fillna(0.02).to_numpy()

    # boost probability if respiratory-like
    prob = np.clip(base_prob * np.where(respiratory_hit.to_numpy(), 1.8, 0.6), 0, 0.95)

    # decide which events get imaging
    attach_mask = rng.random(len(ph)) < prob
    candidates = ph.loc[attach_mask].reset_index(drop=True)

    if candidates.empty:
        # Return empty imaging table with correct columns
        return pd.DataFrame(
            columns=[
                "xray_id",
                "patient_id",
                "history_id",
                "modality",
                "body_part",
                "image_label",
                "file_path",
                "acquired_at",
                "view_position",
                "created_at",
            ]
        )

    # How many images per event (0..max_images_per_event but we already chose events => at least 1)
    if max_images_per_event <= 1:
        n_per_event = np.ones(len(candidates), dtype=int)
    else:
        # 85% 1 image, 15% 2 images (cap at max)
        n_per_event = rng.choice(
            np.arange(1, max_images_per_event + 1),
            size=len(candidates),
            p=_normalize_probs([0.85] + [0.15] + [0.0] * (max_images_per_event - 2)),
        )

    # Flatten events into imaging rows
    repeat_idx = np.repeat(np.arange(len(candidates)), n_per_event)
    rows = candidates.loc[repeat_idx].reset_index(drop=True)

    # Assign label based on diagnosis (pneumonia suggests pneumonia; else normal)
    dx_lower = rows["diagnosis_summary"].fillna("").str.lower()
    wants_pneumonia = dx_lower.str.contains("pneumonia", na=False).to_numpy()

    # Add label noise
    flip = rng.random(len(rows)) < label_noise_prob
    wants_pneumonia = np.where(flip, ~wants_pneumonia, wants_pneumonia)

    # If one label folder missing, force to existing
    if len(x_norm) == 0:
        wants_pneumonia[:] = True
    if len(x_pneu) == 0:
        wants_pneumonia[:] = False

    image_label = np.where(wants_pneumonia, "pneumonia", "normal")

    # Pick file paths (with replacement; safe even if fewer images than rows)
    # Stable, reproducible pick by rng
    file_path = np.empty(len(rows), dtype=object)
    pneu_mask = image_label == "pneumonia"
    norm_mask = ~pneu_mask

    if pneu_mask.any():
        file_path[pneu_mask] = rng.choice(x_pneu, size=pneu_mask.sum(), replace=True)
    if norm_mask.any():
        file_path[norm_mask] = rng.choice(x_norm, size=norm_mask.sum(), replace=True)

    # acquired_at within event window (if end missing, assume short window)
    start = pd.to_datetime(rows["event_start_at"])
    end = pd.to_datetime(rows["event_end_at"], errors="coerce")

    # fallback end = start + 2 hours if missing
    end_filled = end.fillna(start + pd.to_timedelta(120, unit="m"))

    # sample seconds offset uniformly within [0, duration]
    duration_seconds = (
        (end_filled - start).dt.total_seconds().clip(lower=60)
    )  # at least 60s
    offsets = (rng.random(len(rows)) * duration_seconds.to_numpy()).astype(int)
    acquired_at = start + pd.to_timedelta(offsets, unit="s")

    # view position synthetic (optional)
    view_position = rng.choice(
        ["PA", "AP", "Lateral"], p=[0.55, 0.35, 0.10], size=len(rows)
    )

    # Build final imaging table
    xray_id = np.arange(1, len(rows) + 1, dtype=np.int64)

    xray_df = pd.DataFrame(
        {
            "xray_id": xray_id,
            "patient_id": rows["patient_id"].to_numpy(dtype=np.int64),
            "history_id": rows["history_id"].to_numpy(dtype=np.int64),
            "modality": "XRAY",
            "body_part": "chest",
            "image_label": image_label,
            "file_path": file_path,
            "acquired_at": pd.to_datetime(acquired_at),
            "view_position": view_position,
            "created_at": pd.Timestamp.utcnow(),
        }
    )

    # Every history_id must exist in patient_history_df
    if not xray_df["history_id"].isin(patient_history_df["history_id"]).all():
        raise AssertionError(
            "FK violation: some history_id values not present in patient_history_df"
        )

    # patient_id should match the one implied by history_id
    implied_patient = (
        patient_history_df.set_index("history_id")["patient_id"]
        .reindex(xray_df["history_id"])
        .to_numpy()
    )
    if not np.array_equal(
        implied_patient.astype(np.int64), xray_df["patient_id"].to_numpy(dtype=np.int64)
    ):
        raise AssertionError(
            "FK mismatch: patient_id does not match patient_history_df(patient_id) for some history_id"
        )

    return xray_df


# ===== Calendar
def generate_calendar_table(
    doctors_df: pd.DataFrame,
    patient_df: pd.DataFrame,
    start_date: str = "2026-01-17",
    end_date: str = "2026-05-01",
) -> pd.DataFrame:
    """
    Calendar entries for each doctor, weekdays only, 3-4 entries/day/doctor
    within [start_date, end_date] inclusive.
    """
    # inputs / ids
    doctor_ids = doctors_df["doctor_id"].to_numpy(dtype=np.int64)
    patient_ids = patient_df["patient_id"].to_numpy(dtype=np.int64)

    # date range: weekdays only, inclusive
    days = pd.date_range(start=start_date, end=end_date, freq="D")
    days = days[days.weekday < 5]  # Mon-Fri only

    # allowed entry types
    entry_types = np.array(
        [
            "consultation",
            "follow_up",
            "surgery",
            "diagnostic_test",
            "emergency_on_call",
            "telemedicine",
            "meeting",
        ]
    )
    entry_probs = np.array([0.42, 0.16, 0.06, 0.12, 0.06, 0.10, 0.08])
    entry_probs = entry_probs / entry_probs.sum()

    # Which entry types are "with patient"
    patient_meeting_types = {
        "consultation",
        "follow_up",
        "surgery",
        "diagnostic_test",
        "telemedicine",
    }

    # Predefined non-overlapping daily slots (keeps it simple + deterministic)
    # 4 slots, and we sample 3 or 4 per day.
    slots = [
        ("08:00", "09:00"),
        ("10:00", "11:00"),
        ("13:00", "14:00"),
        ("15:00", "16:00"),
    ]

    # Titles/locations
    type_to_title = {
        "consultation": "Consultation",
        "follow_up": "Follow-up appointment",
        "surgery": "Surgery",
        "diagnostic_test": "Diagnostic test",
        "emergency_on_call": "On-call (emergency)",
        "telemedicine": "Telemedicine appointment",
        "meeting": "Meeting",
    }
    location_pool = np.array(
        [
            "Clinic Room 1",
            "Clinic Room 2",
            "Clinic Room 3",
            "Radiology",
            "OR 1",
            "OR 2",
            "Online",
            "Conference Room",
        ]
    )

    status_pool = np.array(["scheduled", "cancelled", "completed"])
    status_probs = np.array([0.92, 0.03, 0.05])

    priority_pool = np.array(["low", "normal", "high"])
    priority_probs = np.array([0.12, 0.78, 0.10])

    rows = []
    calendar_id = 1

    for d_id in doctor_ids:
        for day in days:
            # 3-4 entries per weekday
            n_entries = int(rng.integers(3, 5))  # {3,4}

            # choose distinct slots (no overlap)
            slot_idx = rng.choice(len(slots), size=n_entries, replace=False)

            # assign entry types for each slot
            chosen_types = rng.choice(
                entry_types, p=entry_probs, size=n_entries, replace=True
            )

            for i in range(n_entries):
                et = str(chosen_types[i])
                t_start, t_end = slots[int(slot_idx[i])]

                start_at = pd.Timestamp(f"{day.date()} {t_start}")
                end_at = pd.Timestamp(f"{day.date()} {t_end}")

                # patient linkage only for patient-meeting types
                if et in patient_meeting_types:
                    p_id = int(rng.choice(patient_ids))
                else:
                    p_id = None

                # location: force Online for telemedicine, OR for surgery more often
                if et == "telemedicine":
                    location = "Online"
                elif et == "surgery":
                    location = str(rng.choice(["OR 1", "OR 2"]))
                elif et == "diagnostic_test":
                    location = str(
                        rng.choice(["Radiology", "Clinic Room 2", "Clinic Room 3"])
                    )
                elif et == "meeting":
                    location = str(
                        rng.choice(["Conference Room", "Clinic Room 1", "Online"])
                    )
                elif et == "emergency_on_call":
                    location = str(rng.choice(["Clinic Room 1", "Clinic Room 2"]))
                else:
                    location = str(rng.choice(location_pool))

                # short notes
                if p_id is not None:
                    notes = f"- Patient prep: review recent history\n- Bring latest results if available"
                else:
                    notes = f"- Agenda: {faker.sentence(nb_words=6).rstrip('.')}\n- Action items: {faker.word()}"

                rows.append(
                    {
                        "calendar_id": np.int64(calendar_id),
                        "doctor_id": np.int64(d_id),
                        "patient_id": (np.int64(p_id) if p_id is not None else None),
                        "start_at": start_at,
                        "end_at": end_at,
                        "entry_type": et,
                        "title": type_to_title.get(et, et.replace("_", " ").title()),
                        "location": location,
                        "priority": str(rng.choice(priority_pool, p=priority_probs)),
                        "status": str(rng.choice(status_pool, p=status_probs)),
                        "notes": notes,
                    }
                )
                calendar_id += 1

    calendar_df = pd.DataFrame(rows)

    # FK sanity checks
    if not calendar_df["doctor_id"].isin(doctors_df["doctor_id"]).all():
        raise AssertionError(
            "FK violation: some doctor_id values not present in doctors_df"
        )

    patient_fk_ok = calendar_df["patient_id"].isna() | calendar_df["patient_id"].isin(
        patient_df["patient_id"]
    )
    if not patient_fk_ok.all():
        raise AssertionError(
            "FK violation: some patient_id values not present in patient_df"
        )

    calendar_df["patient_id"] = calendar_df["patient_id"].astype("Int64")
    calendar_df["doctor_id"] = calendar_df["doctor_id"].astype("Int64")
    calendar_df["calendar_id"] = calendar_df["calendar_id"].astype("Int64")

    return calendar_df


if __name__ == "__main__":
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    print(f"Generating synthetic healthcare dataset with faker & SEED={SEED}")

    print("Patient Table...")
    patient_df = generate_patient_table(n_patients=1000)
    print(patient_df)
    patient_df.to_csv(os.path.join(OUTPUT_PATH, "patients.csv"))
    print("Done!")

    print("Doctors Table...")
    doctors_df = generate_doctor_table(n_doctors=100)
    print(doctors_df)
    doctors_df.to_csv(os.path.join(OUTPUT_PATH, "doctors.csv"))
    print("Done!")

    print("Patient History Table...")
    patient_history_df = generate_patient_history_table(
        patient_df=patient_df, doctors_df=doctors_df, n_events=10_000
    )
    print(patient_history_df)
    patient_history_df.to_csv(os.path.join(OUTPUT_PATH, "patient_history.csv"))
    print("Done!")

    print("Patient Xrays Table...")
    xray_index_df = index_xray_files("./data/xrays")
    xray_df = generate_xray_study_table(
        patient_history_df, xray_index_df, max_images_per_event=1
    )
    xray_df.to_csv(os.path.join(OUTPUT_PATH, "xrays.csv"))
    print("Done!")

    print("Calendar Table...")
    calendar_df = generate_calendar_table(
        doctors_df, patient_df, "2026-01-17", "2026-05-01"
    )
    print(calendar_df)
    calendar_df.to_csv(os.path.join(OUTPUT_PATH, "calendars.csv"))
    print(len(calendar_df))
    print("Done!")

    print("Persisting data as a duckdb...")
    save_to_duckdb(
        db_path="./data/garvis.duckdb",
        tables={
            "patient": patient_df,
            "doctor": doctors_df,
            "patient_history": patient_history_df,
            "xray": xray_df,
            "calendar": calendar_df,
        },
    )
    print("Done.")