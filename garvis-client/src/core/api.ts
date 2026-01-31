import { z } from "zod";

const API_BASE = import.meta.env.VITE_API_BASE;
if (!API_BASE) throw new Error("VITE_API_BASE is not defined");

export function apiUrl(path: string): string {
    return `${API_BASE.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
}

export async function fetchAndParse<T>(
    path: string,
    schema: z.ZodType<T>,
    init?: RequestInit
): Promise<T> {
    const res = await fetch(apiUrl(path), {
        headers: { "Accept": "application/json", ...(init?.headers ?? {}) },
        ...init,
    });

    if (!res.ok) {
        // Try to include backend error message if any
        const text = await res.text().catch(() => "");
        throw new Error(`HTTP ${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
    }

    const json = await res.json();
    return schema.parse(json);
}

/**
 * Usage like parseOrThrow(PatientSchema, obj);
 */
export function parseOrThrow<T>(schema: z.ZodType<T>, data: unknown): T {
    return schema.parse(data);
}

/**
 * Usage like safeParse(PatientSchema, obj);
 */
export function safeParse<T>(schema: z.ZodType<T>, data: unknown) {
    return schema.safeParse(data);
}
