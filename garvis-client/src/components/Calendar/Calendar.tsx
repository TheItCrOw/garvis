import { useMemo } from "react";
import type { CalendarEntry } from "../../models/dataModels";
import "./Calendar.css";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faArrowDown,
  faMinus,
  faArrowUp,
} from "@fortawesome/free-solid-svg-icons";

type CalendarProps = {
  entries: CalendarEntry[];
  className?: string;
};

function PriorityIcon({ priority }: { priority?: string | null }) {
  switch (priority) {
    case "high":
      return (
        <FontAwesomeIcon
          icon={faArrowUp}
          className="text-danger me-1"
          title="High priority"
        />
      );
    case "low":
      return (
        <FontAwesomeIcon
          icon={faArrowDown}
          className="text-success me-1"
          title="Low priority"
        />
      );
    case "normal":
    default:
      return (
        <FontAwesomeIcon
          icon={faMinus}
          className="text-secondary me-1"
          title="Normal priority"
        />
      );
  }
}

export function Calendar({ entries, className }: CalendarProps) {
  const sortedEntries = useMemo(() => {
    return [...entries].sort((a, b) => {
      const at = a.start_at?.getTime() ?? Number.POSITIVE_INFINITY;
      const bt = b.start_at?.getTime() ?? Number.POSITIVE_INFINITY;
      return at - bt;
    });
  }, [entries]);

  if (sortedEntries.length === 0) {
    return <div className={"card " + className}>No calendar entries.</div>;
  }

  return (
    <div className={"card calendar p-0 " + className}>
      <h6 className="mb-0 header">
        {sortedEntries[0].start_at?.toLocaleDateString([], {
          weekday: "long",
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
        })}
      </h6>
      <div className="p-2">
        {sortedEntries.map((entry, index) => (
          <div key={entry.calendar_id} className="calendar-entry">
            <div className="d-flex align-items-center justify-content-between">
              <div className="w-100 mb-0 text-start d-flex align-items-center">
                <PriorityIcon priority={entry.priority} />
                <div>
                  <p className="title mb-0">{entry.title}</p>
                  {entry.location && (
                    <p className="mb-0 xsmall text-secondary">
                      ({entry.location})
                    </p>
                  )}
                </div>
              </div>
              <label className="time-range">
                {entry.start_at?.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                –{" "}
                {entry.end_at?.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </label>
            </div>
            <ul className="notes mb-0">
              {entry.notes
                ?.split("-")
                .map((note) =>
                  note.length > 3 ? <li key={note}>{note}</li> : null,
                )}
            </ul>

            {index < sortedEntries.length - 1 && (
              <hr className="mt-2 mb-2" style={{ color: "darkgray" }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
