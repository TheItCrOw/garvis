import { fetchAndParse } from "./api";
import { DoctorSchema, DoctorListSchema, type Doctor } from "../models/dataModels";

export function getDoctor(id: number): Promise<Doctor> {
    return fetchAndParse(`/doctors/${id}`, DoctorSchema);
}

export function getDoctors(): Promise<Doctor[]> {
    return fetchAndParse(`/doctors`, DoctorListSchema);
}
