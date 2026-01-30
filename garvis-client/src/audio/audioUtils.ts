
export function playB64Audio(audioB64: string, mime: string) {
    const bytes = Uint8Array.from(atob(audioB64), c => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);

    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);
    audio.play();
}