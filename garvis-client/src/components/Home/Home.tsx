import { useEffect, useState } from "react";
import type { CalendarEntry } from "../../models/dataModels";
import { Calendar } from "../Calendar/Calendar";
import { getCalendarOfDoctor } from "./../../core/calendar.api";
import { toIsoDateOnlyLocal } from "./../../utils/dateUtils";
import "./Home.css";

export default function Home() {
  const [entries, setEntries] = useState<CalendarEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        // TODO: Use the correct today below and use an appropriate doctor_id!
        //const today = toIsoDateOnlyLocal(new Date());
        const today = "2026-02-03";
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
    <div className="container py-4">
      <div className="text-center mt-0">
        <h1 className="mb-0" style={{ fontSize: "2.1rem" }}>
          Welcome Sir,
        </h1>
        <p className="mb-3 small text-secondary">
          below you find your calendar.
        </p>
        {/* <hr className="mt-2 mb-3 text-secondary" /> */}

        {loading && <p className="text-secondary">Loading…</p>}
        {error && <p className="text-danger">{error}</p>}

        {!loading && !error && <Calendar entries={entries} />}
      </div>
    </div>
  );
}
