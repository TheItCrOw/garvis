import { useEffect, useState } from "react";
import type { CalendarEntry } from "../../models/dataModels";
import { Calendar } from "../Calendar/Calendar";
import { getCalendarOfDoctor } from "./../../core/calendar.api";
import "./Home.css";
import PatientFile from "../PatientFile/PatientFile";
import { toIsoDateOnlyLocal } from "../../utils/dateUtils";
import {
  GarvisOpenView,
  type GarvisInstruction,
} from "../../models/websocket/messages";

type HomeProps = {
  garvisInstruction: GarvisInstruction | null;
};

export default function Home({ garvisInstruction }: HomeProps) {
  const [entries, setEntries] = useState<CalendarEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [patientFileOpen, setPatientFileOpen] = useState(false);
  const [selectedPatientId, setSelectedPatientId] = useState<number | null>(
    null,
  );
  const [historyOpen, setHistoryOpen] = useState(false);

  useEffect(() => {
    if (!garvisInstruction) return;
    console.log(JSON.stringify(garvisInstruction));

    const run = async () => {
      switch (garvisInstruction.open_view) {
        case "Patient":
          setSelectedPatientId(garvisInstruction.parameters.patient_id);
          setPatientFileOpen(true);
          setHistoryOpen(false);
          break;

        case "PatientHistory":
          setSelectedPatientId(garvisInstruction.parameters.patient_id);
          setPatientFileOpen(true);
          setHistoryOpen(true);
          break;

        case GarvisOpenView.Calendar: {
          console.log("Reloading Calendar");
          const doctorId = garvisInstruction.parameters?.doctor_id ?? 1;
          const day = garvisInstruction.parameters?.date ?? "";
          if (day == "") break;

          setPatientFileOpen(false);

          setLoading(true);
          setError(null);

          try {
            const data = await getCalendarOfDoctor(doctorId, day);
            console.log(data);
            setEntries(data);
          } catch (e) {
            const msg =
              e instanceof Error ? e.message : "Failed to load calendar";
            setError(msg);
            setEntries([]);
          } finally {
            setLoading(false);
          }

          break;
        }

        default:
          console.log("open_view was given, but it was unrecognizable.");
      }
    };

    run();
  }, [garvisInstruction]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        // TODO: Use the correct today below and use an appropriate doctor_id!
        const today = toIsoDateOnlyLocal(new Date());
        //const today = "2026-02-03";
        const data = await getCalendarOfDoctor(1, today);
        if (!cancelled) setEntries(data);
      } catch (e) {
        if (!cancelled) {
          const msg =
            e instanceof Error ? e.message : "Failed to load calendar";
          setError(msg);
          setEntries([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <div className="container py-4">
        <div className="text-center mt-0">
          <h1 className="mb-0" style={{ fontSize: "2.1rem" }}>
            Welcome,
          </h1>
          <p className="mb-4 small text-secondary">
            below you find your calendar.
          </p>
          {/* <hr className="mt-2 mb-3 text-secondary" /> */}

          {loading && <p className="text-secondary">Loading…</p>}
          {error && <p className="text-danger">{error}</p>}

          {!loading && !error && (
            <Calendar
              entries={entries}
              onCalendarEntryClicked={(entry) => {
                if (entry.patient_id == null) return;
                setSelectedPatientId(entry.patient_id);
                setPatientFileOpen(true);
              }}
            />
          )}
        </div>

        <PatientFile
          isOpen={patientFileOpen}
          patient_id={selectedPatientId}
          onClose={() => {
            setPatientFileOpen(false);
            setHistoryOpen(false); // optional but recommended
          }}
          historyIsOpen={historyOpen}
          onHistoryOpen={() => setHistoryOpen(true)}
          onHistoryClose={() => setHistoryOpen(false)}
        />
      </div>
    </>
  );
}
