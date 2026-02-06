import { z } from "zod";

/* ======== Date primitives ======== */

/**
 * Backend datetime: ISO 8601 string -> Date
 * Examples:
 *  - 2026-01-31T12:34:56Z
 *  - 2026-01-31T12:34:56+01:00
 */
export const DateTimeSchema = z
    .string()
    .refine(
        (s) => !Number.isNaN(Date.parse(s)),
        "Invalid datetime"
    )
    .transform((s) => new Date(s));

/**
 * Backend date-only: "YYYY-MM-DD" -> Date (UTC midnight)
 */
export const DateOnlySchema = z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Expected YYYY-MM-DD")
    .transform((s) => {
        const [y, m, d] = s.split("-").map(Number);
        return new Date(Date.UTC(y, m - 1, d, 0, 0, 0));
    });

export const NullableDateTime = DateTimeSchema.nullable();
export const NullableDateOnly = DateOnlySchema.nullable();

/* ======== Patient ======== */

export const PatientSchema = z.object({
    patient_id: z.number(),
    created_at: DateTimeSchema,

    first_name: z.string().nullable(),
    last_name: z.string().nullable(),
    sex: z.string().nullable(),
    date_of_birth: DateTimeSchema,

    deceased_flag: z.boolean().nullable(),
    marital_status: z.string().nullable(),
    language: z.string().nullable(),

    email: z.string().email().nullable(),
    phone: z.string().nullable(),

    address_line1: z.string().nullable(),
    address_line2: z.string().nullable(),
    city: z.string().nullable(),
    state: z.string().nullable(),
    postal_code: z.string().nullable(),
    country: z.string().nullable(),

    primary_care_provider_id: z.number().nullable(),
    organization_id: z.number().nullable(),
    insurance_plan_id: z.number().nullable(),

    active_flag: z.boolean().nullable(),
    last_seen_at: DateTimeSchema.nullable(),

    height_cm: z.number().nullable(),
    weight_kg: z.number().nullable(),
    bmi: z.number().nullable(),

    smoking_status: z.string().nullable(),
    alcohol_use: z.string().nullable(),
    pregnancy_status: z.string().nullable(),

    has_diabetes: z.boolean().nullable(),
    has_hypertension: z.boolean().nullable(),
    has_copd: z.boolean().nullable(),
    has_ckd: z.boolean().nullable(),
    has_asthma: z.boolean().nullable(),

    updated_at: NullableDateTime,
});

export type Patient = z.infer<typeof PatientSchema>;
export const PatientListSchema = z.array(PatientSchema);

/* ======== Doctor ======== */

export const DoctorSchema = z.object({
    doctor_id: z.number(),
    first_name: z.string().nullable(),
    last_name: z.string().nullable(),
    sex: z.string().nullable(),
    specialty: z.string().nullable(),
    years_of_experience: z.number().int().nullable(),
    email: z.string().email().nullable(),
    phone: z.string().nullable(),
    age: z.number().int().nullable(),
});

export type Doctor = z.infer<typeof DoctorSchema>;
export const DoctorListSchema = z.array(DoctorSchema);

/* ======== CalendarEntry ======== */

export const CalendarEntrySchema = z.object({
    calendar_id: z.number(),
    doctor_id: z.number().nullable(),
    patient_id: z.number().nullable(),

    start_at: NullableDateTime,
    end_at: NullableDateTime,

    entry_type: z.string().nullable(),
    title: z.string().nullable(),
    location: z.string().nullable(),
    priority: z.string().nullable(),
    status: z.string().nullable(),
    notes: z.string().nullable(),
});

export type CalendarEntry = z.infer<typeof CalendarEntrySchema>;
export const CalendarEntryListSchema = z.array(CalendarEntrySchema);

/* ======== PatientHistory ======== */

export const PatientHistorySchema = z.object({
    history_id: z.number(),
    patient_id: z.number().nullable(),
    doctor_id: z.number().nullable(),

    event_type: z.string().nullable(),
    event_start_at: NullableDateTime,
    event_end_at: NullableDateTime,

    chief_complaint: z.string().nullable(),
    diagnosis_summary: z.string().nullable(),
    procedure_performed: z.string().nullable(),
    prescription_given: z.string().nullable(),
    notes: z.string().nullable(),

    outcome: z.string().nullable(),
    follow_up_required: z.boolean().nullable(),
    severity: z.string().nullable(),
    xray_img_id: z.number().nullable(),

    created_at: NullableDateTime,
});

export type PatientHistory = z.infer<typeof PatientHistorySchema>;
export const PatientHistoryListSchema = z.array(PatientHistorySchema);