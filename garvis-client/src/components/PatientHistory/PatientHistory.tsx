import React, { useEffect, useMemo, useState } from "react";
import "./PatientHistory.css";

import type { PatientHistory } from "../../models/dataModels";
import { getPatientHistory } from "../../core/patients.api";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faIdBadge, faUserDoctor } from "@fortawesome/free-solid-svg-icons";
import { capitalize } from "../../utils/stringUtils";
import { buildXrayImageUrl } from "../../core/xrays.api";

type PatientHistoryPopupProps = {
  isOpen: boolean;
  onClose: () => void;
  history?: PatientHistory[] | null;
  patient_id?: number | null;
  className?: string;
};

export default function PatientHistoryPopup({
  isOpen,
  onClose,
  history,
  patient_id,
  className,
}: PatientHistoryPopupProps) {
  const [fetchedHistory, setFetchedHistory] = useState<PatientHistory[] | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [shouldRender, setShouldRender] = useState(isOpen);
  const [animateOpen, setAnimateOpen] = useState(false);

  const data = history ?? fetchedHistory;

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

  // Fetch only when opened AND history not provided
  useEffect(() => {
    if (!isOpen) return;
    if (history) {
      setFetchedHistory(null);
      setError(null);
      setLoading(false);
      return;
    }

    if (patient_id == null) {
      setFetchedHistory(null);
      setError("Missing history or patient_id.");
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getPatientHistory(patient_id)
      .then((items) => {
        if (!cancelled) setFetchedHistory(items);
      })
      .catch((e: unknown) => {
        if (!cancelled)
          setError(
            e instanceof Error ? e.message : "Failed to load patient history.",
          );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, history, patient_id]);

  // Close on ESC
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  const sorted = useMemo(() => {
    if (!data) return null;
    return [...data].sort((a, b) => {
      const at = a.event_start_at?.getTime() ?? -Infinity;
      const bt = b.event_start_at?.getTime() ?? -Infinity;
      return bt - at; // newest first
    });
  }, [data]);

  if (!shouldRender) return null;

  const overlayStateClass = animateOpen ? "ph-open" : "ph-closed";

  return (
    <div
      className={`ph-overlay ${overlayStateClass} ${className ?? ""}`}
      onMouseDown={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div className="ph-sheet" onMouseDown={(e) => e.stopPropagation()}>
        <div className="ph-header">
          <div className="ph-title">
            Patient History
            {patient_id != null ? ` - Patient #${patient_id}` : ""}
          </div>

          <button
            className="ph-close"
            onClick={onClose}
            aria-label="Close patient history"
            title="Close"
          >
            ✕
          </button>
        </div>

        <div className="ph-content">
          {loading && <div className="ph-state">Loading…</div>}
          {!loading && error && (
            <div className="ph-state ph-error">{error}</div>
          )}
          {!loading && !error && (!sorted || sorted.length === 0) && (
            <div className="ph-state">No history entries.</div>
          )}

          {!loading && !error && sorted && sorted.length > 0 && (
            <div className="ph-list">
              {sorted.map((h) => (
                <div key={h.history_id} className="card ph-card">
                  <div className="card-body">
                    <div className="d-flex align-items-start justify-content-between gap-2">
                      <div>
                        <div className="ph-event-type">
                          {capitalize(h.event_type ?? "/")}
                          {h.severity ? (
                            <span className="ph-pill">{h.severity}</span>
                          ) : null}
                          {h.follow_up_required != null ? (
                            <span
                              className={`ph-pill ${h.follow_up_required ? "ph-pill-warn" : "ph-pill-ok"}`}
                            >
                              follow-up: {h.follow_up_required ? "yes" : "no"}
                            </span>
                          ) : null}
                        </div>

                        <div className="ph-meta">
                          <span>
                            {h.event_start_at
                              ? h.event_start_at.toLocaleDateString([], {
                                  year: "numeric",
                                  month: "2-digit",
                                  day: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })
                              : "/"}{" "}
                            {"-"}{" "}
                            {h.event_end_at
                              ? h.event_end_at.toLocaleDateString([], {
                                  year: "numeric",
                                  month: "2-digit",
                                  day: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })
                              : "/"}
                          </span>
                        </div>
                      </div>

                      <div className="ph-ids text-end">
                        <div className="ph-id">Id: {h.history_id}</div>
                        <div className="ph-id doc mt-1">
                          <FontAwesomeIcon icon={faUserDoctor} size="lg" />{" "}
                          {h.doctor_id ?? "/"}
                        </div>
                      </div>
                    </div>

                    {h.xray_img_id && (
                      <div className="mt-3">
                        <div className="xray-img">
                          <img src={buildXrayImageUrl(h.xray_img_id)} />
                        </div>
                        <p className="mb-0 mt-1 xsmall text-secondary text-end w-100">
                          <FontAwesomeIcon icon={faIdBadge} /> Image Id:{" "}
                          {h.xray_img_id}
                        </p>
                      </div>
                    )}

                    <div className="row mt-2">
                      <div className="col-6">
                        <div className="ph-label">Complaint</div>
                        <div className="ph-value">
                          {h.chief_complaint ?? "/"}
                        </div>
                      </div>

                      <div className="col-6">
                        <div className="ph-label">Diagnosis Summary</div>
                        <div className="ph-value">
                          {h.diagnosis_summary ?? "/"}
                        </div>
                      </div>

                      <div className="col-6 mt-1 mt-md-0">
                        <div className="ph-label">Procedure Performed</div>
                        <div className="ph-value">
                          {h.procedure_performed ?? "/"}
                        </div>
                      </div>

                      <div className="col-6 mt-1 mt-md-0">
                        <div className="ph-label">Prescription</div>
                        <div className="ph-value">
                          {h.prescription_given ?? "/"}
                        </div>
                      </div>

                      <div className="col-6 mt-1">
                        <div className="ph-label">Outcome</div>
                        <div className="ph-value">{h.outcome ?? "/"}</div>
                      </div>

                      {/* <div className="col-6 mt-1">
                        <div className="ph-label">created_at</div>
                        <div className="ph-value">
                          {h.created_at?.toLocaleDateString([], {
                            year: "numeric",
                            month: "2-digit",
                            day: "2-digit",
                          }) ?? "/"}
                        </div>
                      </div> */}

                      <div className="col-12 mt-1">
                        <div className="ph-label">notes</div>
                        <div className="ph-value ph-notes">
                          <ul className="notes mb-0">
                            {h.notes
                              ?.split("-")
                              .map((note) =>
                                note.length > 3 ? (
                                  <li key={note}>{note}</li>
                                ) : null,
                              )}
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
