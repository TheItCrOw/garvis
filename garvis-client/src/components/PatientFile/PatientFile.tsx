import React, { useEffect, useState } from "react";
import "./PatientFile.css";

import type { Patient } from "../../models/dataModels";
import { getPatient } from "../../core/patients.api";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faUser } from "@fortawesome/free-solid-svg-icons";
import PatientHistoryPopup from "../PatientHistory/PatientHistory";

type PatientFileProps = {
  isOpen: boolean;
  onClose: () => void;

  patient?: Patient | null;
  patient_id?: number | null;

  className?: string;
};

export default function PatientFile({
  isOpen,
  onClose,
  patient,
  patient_id,
  className,
}: PatientFileProps) {
  const [fetchedPatient, setFetchedPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [openHistory, setOpenHistory] = useState(false);
  const [patientId, setPatientId] = useState<number | null>(null);

  const [shouldRender, setShouldRender] = useState(isOpen);
  const [animateOpen, setAnimateOpen] = useState(false);

  const data = patient ?? fetchedPatient;

  // Mount/unmount + ensure open animation plays
  useEffect(() => {
    if (isOpen) {
      setShouldRender(true);

      setAnimateOpen(false);
      const raf = requestAnimationFrame(() => setAnimateOpen(true));

      return () => cancelAnimationFrame(raf);
    }

    setAnimateOpen(false);
    const t = window.setTimeout(() => setShouldRender(false), 220);
    return () => window.clearTimeout(t);
  }, [isOpen]);

  // Fetch only when opened AND no patient object is provided
  useEffect(() => {
    if (!isOpen) return;

    if (patient) {
      setFetchedPatient(null);
      setError(null);
      setLoading(false);
      return;
    }

    if (patient_id == null) {
      setFetchedPatient(null);
      setError("Missing patient or patient_id.");
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getPatient(patient_id)
      .then((p) => {
        if (!cancelled) setFetchedPatient(p);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "Failed to load patient.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, patient, patient_id]);

  // Close on ESC
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!shouldRender) return null;

  const overlayStateClass = animateOpen ? "pf-open" : "pf-closed";

  return (
    <>
      {/* The patient history popup which can be opened. */}
      <PatientHistoryPopup
        isOpen={openHistory}
        patient_id={patientId}
        onClose={() => setOpenHistory(false)}
      />

      {/* The actual file */}
      <div
        className={`pf-overlay ${overlayStateClass} ${className ?? ""}`}
        onMouseDown={onClose}
        role="dialog"
        aria-modal="true"
      >
        <div className="pf-sheet" onMouseDown={(e) => e.stopPropagation()}>
          <div className="pf-header">
            <div className="pf-title">
              <FontAwesomeIcon icon={faUser} className="me-2" size="lg" />
              {data?.first_name} {data?.last_name}
            </div>

            <button
              className="pf-close"
              onClick={onClose}
              aria-label="Close patient file"
              title="Close"
            >
              ✕
            </button>
          </div>

          {/* open patient history */}
          <div className="w-100">
            <button
              className="btn open-patient-history-btn"
              onClick={() => {
                setPatientId(fetchedPatient?.patient_id ?? null);
                setOpenHistory(true);
              }}
            >
              Open Patient History
            </button>
          </div>

          <div className="pf-content">
            {loading && <div className="pf-state">Loading…</div>}
            {!loading && error && (
              <div className="pf-state pf-error">{error}</div>
            )}
            {!loading && !error && !data && (
              <div className="pf-state">No data.</div>
            )}

            {!loading && !error && data && (
              <div className="row">
                <div className="col-6 label-value-pair">
                  <div className="pf-label">Patient Id</div>
                  <div className="pf-value">{data.patient_id ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Created</div>
                  <div className="pf-value">
                    {data.created_at?.toLocaleDateString([], {
                      weekday: "long",
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                    }) ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">First Name</div>
                  <div className="pf-value">{data.first_name ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Last Name</div>
                  <div className="pf-value">{data.last_name ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Sex</div>
                  <div className="pf-value">{data.sex ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Birthday</div>
                  <div className="pf-value">
                    {data.date_of_birth?.toLocaleDateString([], {
                      weekday: "long",
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                    }) ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Deceased</div>
                  <div className="pf-value">
                    {data.deceased_flag?.toString() ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Marital Status</div>
                  <div className="pf-value">{data.marital_status ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Language</div>
                  <div className="pf-value">{data.language ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Email</div>
                  <div className="pf-value">{data.email ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Phone</div>
                  <div className="pf-value">{data.phone ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Address Line 1</div>
                  <div className="pf-value">{data.address_line1 ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Address Line 2</div>
                  <div className="pf-value">{data.address_line2 ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">City</div>
                  <div className="pf-value">{data.city ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">State</div>
                  <div className="pf-value">{data.state ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Postal Code</div>
                  <div className="pf-value">{data.postal_code ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Country</div>
                  <div className="pf-value">{data.country ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Care Provider Id</div>
                  <div className="pf-value">
                    {data.primary_care_provider_id ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Organization Id</div>
                  <div className="pf-value">{data.organization_id ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Insurance Id</div>
                  <div className="pf-value">
                    {data.insurance_plan_id ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Active Patient</div>
                  <div className="pf-value">
                    {data.active_flag?.toString() ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Last Visit</div>
                  <div className="pf-value">
                    {data.last_seen_at?.toLocaleDateString([], {
                      weekday: "long",
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                    }) ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Height (cm)</div>
                  <div className="pf-value">{data.height_cm ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Weight (kg)</div>
                  <div className="pf-value">{data.weight_kg ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">BMI</div>
                  <div className="pf-value">{data.bmi ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Smoking Status</div>
                  <div className="pf-value">{data.smoking_status ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Alcohol Usage</div>
                  <div className="pf-value">{data.alcohol_use ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Is Pregnant</div>
                  <div className="pf-value">{data.pregnancy_status ?? "/"}</div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Has Diabetes</div>
                  <div className="pf-value">
                    {data.has_diabetes?.toString() ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Has Hypertension</div>
                  <div className="pf-value">
                    {data.has_hypertension?.toString() ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Has COPD</div>
                  <div className="pf-value">
                    {data.has_copd?.toString() ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Has CKD</div>
                  <div className="pf-value">
                    {data.has_ckd?.toString() ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Has Asthma</div>
                  <div className="pf-value">
                    {data.has_asthma?.toString() ?? "/"}
                  </div>
                </div>

                <div className="col-6 label-value-pair">
                  <div className="pf-label">Last Update</div>
                  <div className="pf-value">
                    {data.updated_at?.toLocaleDateString([], {
                      weekday: "long",
                      year: "numeric",
                      month: "2-digit",
                      day: "2-digit",
                    }) ?? "/"}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
