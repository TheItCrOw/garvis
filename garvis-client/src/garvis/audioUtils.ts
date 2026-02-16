let currentAudio: HTMLAudioElement | null = null;
let currentObjectUrl: string | null = null;

type PlayOptions = {
    onSpeakingChange?: (speaking: boolean) => void;
};

export function stopCurrentAudio() {
    if (!currentAudio) return;

    try {
        currentAudio.pause();
        currentAudio.currentTime = 0;
    } finally {
        if (currentObjectUrl) {
            URL.revokeObjectURL(currentObjectUrl);
            currentObjectUrl = null;
        }
        currentAudio = null;
    }
}

export async function playB64Audio(audioB64: string, mime: string, opts?: PlayOptions) {
    // Stop any audio already playing
    stopCurrentAudio();

    const bytes = Uint8Array.from(atob(audioB64), (c) => c.charCodeAt(0));
    const blob = new Blob([bytes], { type: mime });
    const url = URL.createObjectURL(blob);

    const audio = new Audio(url);
    currentAudio = audio;
    currentObjectUrl = url;

    const setSpeaking = (v: boolean) => opts?.onSpeakingChange?.(v);

    const cleanup = () => {
        // Only clean up if this is still the active audio (avoid races)
        if (currentAudio === audio) {
            if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
            currentObjectUrl = null;
            currentAudio = null;
        }
        setSpeaking(false);
    };

    audio.onplay = () => setSpeaking(true);
    audio.onended = cleanup;
    audio.onpause = () => {
        // pause can happen from stopCurrentAudio or user/system
        // if paused because it ended, onended will run; otherwise keep consistent:
        if (!audio.ended) cleanup();
    };
    audio.onerror = cleanup;

    try {
        await audio.play(); // may throw if not unlocked
    } catch (e) {
        cleanup();
        throw e;
    }
}

export function playSound(sound: string): Promise<void> {
    return new Promise((resolve) => {
        const audio = new Audio(sound);
        audio.volume = 0.6;

        audio.onended = () => resolve();

        // Fallback resolve in case onended doesn’t fire
        setTimeout(resolve, 1200);

        audio.play().catch(() => resolve());
    });
}
