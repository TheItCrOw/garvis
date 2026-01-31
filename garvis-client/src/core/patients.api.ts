import { fetchAndParse } from "./api";
import { PatientSchema, PatientListSchema, type Patient } from "../models/dataModels";

export function getPatient(id: number): Promise<Patient> {
    return fetchAndParse(`/patients/${id}`, PatientSchema);
}

export function getPatients(): Promise<Patient[]> {
    return fetchAndParse(`/patients`, PatientListSchema);
}
