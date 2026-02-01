import { fetchAndParse } from "./api";
import { PatientSchema, PatientListSchema, type Patient } from "../models/dataModels";

export function getPatient(patient_id: number): Promise<Patient> {
    return fetchAndParse(`/patients/${patient_id}`, PatientSchema);
}

export function getPatients(): Promise<Patient[]> {
    return fetchAndParse(`/patients`, PatientListSchema);
}
