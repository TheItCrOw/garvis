import { fetchAndParse } from "./api";
import { CalendarEntryListSchema, type CalendarEntry } from "../models/dataModels";

export function getCalendarOfDoctor(doctor_id: number, day?: string): Promise<CalendarEntry[]> {
    const qs = day ? `?day=${encodeURIComponent(day)}` : "";
    return fetchAndParse(`/calendar/${doctor_id}${qs}`, CalendarEntryListSchema);
}

