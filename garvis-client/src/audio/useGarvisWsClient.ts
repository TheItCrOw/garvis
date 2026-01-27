/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useRef, useState } from "react";
import { AudioWsClient } from "./GarvisWsClient";
import { createWsStartContent } from "../models/websocket/messages";

type UsePushToTalkOptions = {
    wsUrl: string;
};

export function usePushToTalkAudio({ wsUrl }: UsePushToTalkOptions) {
    const [isRecording, setIsRecording] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const clientRef = useRef<AudioWsClient | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const ctxRef = useRef<AudioContext | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);

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

            // Do NOT hard-close immediately; ask server to stop and wait for END.
            if (clientRef.current && clientRef.current.isOpen()) {
                clientRef.current.sendStop({ reason: "user_released" });
            }
        } finally {
            // UI: we can flip immediately, server will close shortly after END
            setIsRecording(false);
        }
    }, []);

    const start = useCallback(async () => {
        if (isRecording) return;
        setError(null);

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
            });
            streamRef.current = stream;

            const ctx = new AudioContext({ latencyHint: "interactive" });
            ctxRef.current = ctx;
            await ctx.resume();

            const workletUrl = new URL("../audio/pcm-worklet.js", import.meta.url);
            await ctx.audioWorklet.addModule(workletUrl);

            const source = ctx.createMediaStreamSource(stream);
            const workletNode = new AudioWorkletNode(ctx, "pcm16-processor");
            workletNodeRef.current = workletNode;

            // Safari keep-alive
            const silentGain = ctx.createGain();
            silentGain.gain.value = 0;
            source.connect(workletNode);
            workletNode.connect(silentGain).connect(ctx.destination);

            const client = new AudioWsClient(wsUrl);
            clientRef.current = client;

            client.onError((m) => setError(m.content.message));
            client.onEnd(() => {
                // server finished; close and stop UI state
                client.close();
                setIsRecording(false);
            });

            // debug transcripts
            client.onTranscript((m) => {
                console.log(`[${m.content.final ? "FINAL" : "INTERIM"}]`, m.content.text);
            });

            client.onRawMessage((msg) => {
                console.log("[WS ⬅]", msg);
            });

            await client.connect();

            // Worklet outputs 16k mono PCM16LE frames (see pcm-worklet.js below)
            client.sendStart(
                createWsStartContent("pcm16le", 16000, 1, true, "en-US")
            );

            workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
                client.sendAudioFrame(event.data);
            };

            setIsRecording(true);
        } catch (e: any) {
            setError(e?.message ?? "Failed to start audio.");
            await cleanup();
        }
    }, [cleanup, isRecording, wsUrl]);

    const stop = useCallback(async () => {
        if (!isRecording) return;
        await cleanup();
    }, [cleanup, isRecording]);

    return { start, stop, isRecording, error };
}
