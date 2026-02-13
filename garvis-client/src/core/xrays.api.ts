import type { WsGarvisContent } from "../models/websocket/messages";

const API_BASE = import.meta.env.VITE_API_BASE;
if (!API_BASE) throw new Error("VITE_API_BASE is not defined");

export function buildXrayImageUrl(xray_id: number) {
    return `${API_BASE}/xrays/${xray_id}/image`
}

/**
 * Returns the raw image blob
 */
export async function getXrayImageBlobById(xray_id: number): Promise<Blob> {
    const res = await fetch(buildXrayImageUrl(xray_id));

    if (!res.ok) {
        throw new Error(`Failed to fetch xray image ${xray_id}`);
    }

    return await res.blob();
}

/**
 * Helper: returns a URL usable directly in <img src={...} />
 */
export async function getXrayImageSrcById(xray_id: number): Promise<string> {
    const blob = await getXrayImageBlobById(xray_id);
    return URL.createObjectURL(blob);
}

/**
 * Analyze an xray image by Garvis through the xray_id and the current session_id
 */
export async function analyzeXrayImgById(
    xray_id: number,
    session_id: string
): Promise<WsGarvisContent> {

    const res = await fetch(
        `${API_BASE}/xrays/${xray_id}/garvis_analyze?session_id=${session_id}`
    );

    if (!res.ok) {
        throw new Error(`Failed to fetch xray analysis ${xray_id}`);
    }

    const data: WsGarvisContent = await res.json();
    return data;
}
