/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useRef, useState } from "react";

type UsePushToTalkOptions = {
    wsUrl: string; // websocket backend, e.g. "ws://localhost:8000/ws/audio"
};

export function usePushToTalkAudio({ wsUrl }: UsePushToTalkOptions) {
    const [isRecording, setIsRecording] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const ctxRef = useRef<AudioContext | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);

    const start = useCallback(async () => {
        if (isRecording) return;
        setError(null);

        try {
            // 1) Mic permission + stream
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            streamRef.current = stream;

            // 2) AudioContext (must be started from a user gesture on iOS)
            const ctx = new AudioContext();
            ctxRef.current = ctx;

            // 3) Load AudioWorklet module
            const workletUrl = new URL("./pcm-worklet.js", import.meta.url);
            await ctx.audioWorklet.addModule(workletUrl);

            // 4) Create nodes
            const source = ctx.createMediaStreamSource(stream);
            const workletNode = new AudioWorkletNode(ctx, "pcm16-processor");
            workletNodeRef.current = workletNode;

            // Safari sometimes needs a destination connection to keep processing alive:
            const silentGain = ctx.createGain();
            silentGain.gain.value = 0;

            source.connect(workletNode);
            workletNode.connect(silentGain).connect(ctx.destination);

            // 5) WebSocket
            const ws = new WebSocket(wsUrl);
            ws.binaryType = "arraybuffer";
            wsRef.current = ws;

            ws.onopen = () => {
                // Send a small control message first (useful for backend)
                ws.send(
                    JSON.stringify({
                        type: "start",
                        format: "pcm16le",
                        sampleRate: ctx.sampleRate,
                        channels: 1,
                    })
                );

                // Stream PCM frames
                workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
                    if (ws.readyState === WebSocket.OPEN) {
                        ws.send(event.data); // ArrayBuffer (PCM16LE)
                    }
                };

                setIsRecording(true);
            };

            ws.onerror = () => {
                setError("WebSocket error.");
            };

            ws.onclose = () => {
                // If server closes unexpectedly, stop locally
                // (avoid calling stop() here to prevent loops; just update state)
                setIsRecording(false);
            };
        } catch (e: any) {
            setError(e?.message ?? "Failed to start audio.");
            // Cleanup partial init
            await cleanup();
        }
    }, [isRecording, wsUrl]);

    const cleanup = useCallback(async () => {
        try {
            workletNodeRef.current?.disconnect();
            workletNodeRef.current = null;

            if (ctxRef.current) {
                await ctxRef.current.close();
                ctxRef.current = null;
            }

            if (streamRef.current) {
                streamRef.current.getTracks().forEach((t) => t.stop());
                streamRef.current = null;
            }

            if (wsRef.current) {
                try {
                    if (wsRef.current.readyState === WebSocket.OPEN) {
                        wsRef.current.send(JSON.stringify({ type: "stop" }));
                    }
                } catch {
                    // ignore
                }
                wsRef.current.close();
                wsRef.current = null;
            }
        } finally {
            setIsRecording(false);
        }
    }, []);

    const stop = useCallback(async () => {
        if (!isRecording) return;
        await cleanup();
    }, [cleanup, isRecording]);

    return { start, stop, isRecording, error };
}
