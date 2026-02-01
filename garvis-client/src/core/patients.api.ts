import { fetchAndParse } from "./api";
import { PatientSchema, PatientListSchema, type Patient, type PatientHistory, PatientHistoryListSchema } from "../models/dataModels";

export function getPatient(patient_id: number): Promise<Patient> {
    return fetchAndParse(`/patients/${patient_id}`, PatientSchema);
}

export function getPatientHistory(patient_id: number): Promise<PatientHistory[]> {
    return fetchAndParse(`/patients/history/${patient_id}`, PatientHistoryListSchema);
}


export function getPatients(): Promise<Patient[]> {
    return fetchAndParse(`/patients`, PatientListSchema);
}
