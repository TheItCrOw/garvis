const API_BASE = import.meta.env.VITE_API_BASE;
if (!API_BASE) throw new Error("VITE_API_BASE is not defined");

/**
 * Sends recorded audio blob to MedASR backend
 */
export async function transcribeMedicalAudio(
    audioBlob: Blob
): Promise<{ text: string }> {

    const formData = new FormData();
    formData.append("uploaded_file", audioBlob, "recording.wav");

    const res = await fetch(`${API_BASE}/medasr/transcribe`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        throw new Error("Failed to transcribe audio");
    }

    return await res.json();
}
