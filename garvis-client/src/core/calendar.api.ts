import { fetchAndParse } from "./api";
import { CalendarEntrySchema, CalendarEntryListSchema, type CalendarEntry } from "../models/dataModels";

export function getCalendarOfDoctor(doctor_id: number, day?: string): Promise<CalendarEntry[]> {
    const qs = day ? `?day=${encodeURIComponent(day)}` : "";
    return fetchAndParse(`/calendar/${doctor_id}${qs}`, CalendarEntryListSchema);
}

export function updateClosestMeetingNotes(
    doctor_id: number,
    notes?: string | null
): Promise<CalendarEntry> {
    const params = new URLSearchParams({
        doctor_id: String(doctor_id),
    });

    if (notes != null) {
        params.append("notes", notes);
    }

    return fetchAndParse(
        `/calendar/closest-meeting/notes?${params.toString()}`,
        CalendarEntrySchema
    );
}