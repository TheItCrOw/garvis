/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useEffect, useRef, useState } from "react";
import { GarvisWsClient } from "./GarvisWsClient";
import { createWsStartRecordingContent, GarvisOpenView, type GarvisInstruction } from "../models/websocket/messages";
import { playB64Audio, stopCurrentAudio } from "./audioUtils"

type UseGarvisWsClientOptions = {
    wsUrl: string;
    onGarvisInstruction: (instruction: GarvisInstruction) => void;
};

export function useGarvisWsClient({ wsUrl, onGarvisInstruction }: UseGarvisWsClientOptions) {
    const [isRecording, setIsRecording] = useState(false);
    const [garvisIsSpeaking, setGarvisIsSpeaking] = useState(false);
    const [garvisIsThinking, setGarvisIsThinking] = useState(false);
    const [wsIsConnected, setWsIsConnected] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [transcripts, setTranscripts] = useState<string[]>([]);

    const didInitRef = useRef(false);
    const clientRef = useRef<GarvisWsClient | null>(null);
    const connectingRef = useRef<Promise<void> | null>(null);

    const streamRef = useRef<MediaStream | null>(null);
    const audioCtxRef = useRef<AudioContext | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);

    const stopGarvisSpeech = useCallback(() => {
        stopCurrentAudio();
        setGarvisIsSpeaking(false);
    }, []);

    const setupClientHandlersOnce = useCallback((client: GarvisWsClient) => {
        client.onError((m) => setError(m.content.message));

        client.onEnd(() => {
            setIsRecording(false);
        });

        client.onTranscript((m) => {
            setTranscripts([m.content.text]);
            setGarvisIsThinking(true);
            console.log(`[${m.content.final ? "FINAL" : "INTERIM"}]`, m.content.text);
        });

        client.onGarvis((m) => {
            console.log(`[GARVIS] ${m.content.intent}: ${m.content.answer}`);
            // Stop any speech that is currently playing
            stopCurrentAudio();
            setGarvisIsThinking(false);

            // If Garvis tells us to open a view or apply an action, check it and execute it
            if (m.content.open_view !== undefined && m.content.open_view !== "") {
                const view = m.content.open_view as string;

                if (!Object.values(GarvisOpenView).includes(view as GarvisOpenView)) {
                    return; // screw it, we don't have that view action then.
                }
                console.log(`Received instructions from Garvis: 
                    open_view=${m.content.open_view}; 
                    action=${m.content.action}; 
                    parameters=${JSON.stringify(m.content.parameters)}`);

                const open_view = view as GarvisOpenView;
                onGarvisInstruction({
                    open_view,
                    parameters: m.content.parameters as any,
                });
            }

            // Make the new message speak
            if (m.content.audio_base64 && m.content.audio_mime_type) {
                playB64Audio(m.content.audio_base64, m.content.audio_mime_type, {
                    onSpeakingChange: setGarvisIsSpeaking,
                }).catch((e) => {
                    console.warn("Audio play failed:", e);
                    setGarvisIsSpeaking(false);
                });
            } else {
                setGarvisIsSpeaking(false);
            }
        });

        client.onRawMessage((msg) => {
            console.log("[WS ⬅]", msg);
        });
    }, []);

    useEffect(() => {
        if (didInitRef.current) return;
        didInitRef.current = true;

        let cancelled = false;

        (async () => {
            console.log("Initiating Websocket Connection...");

            try {
                if (!clientRef.current) {
                    const client = new GarvisWsClient(wsUrl);
                    clientRef.current = client;
                    console.log("Connected!")
                    setupClientHandlersOnce(client);
                    setWsIsConnected(true);
                }

                // If already open, just mark connected
                if (clientRef.current.isOpen()) {
                    console.log("Websocket already open.");
                    if (!cancelled) setWsIsConnected(true);
                    return;
                }

                // Prevent parallel connects
                if (connectingRef.current) {
                    console.log("Waiting for existing connect...");
                    await connectingRef.current;
                    return;
                }

                const p = clientRef.current.connect();
                connectingRef.current = p;

                await p;
                connectingRef.current = null;

                console.log("Websocket connected. client.isOpen =", clientRef.current.isOpen());
                if (!cancelled) setWsIsConnected(true);
            } catch (e: any) {
                connectingRef.current = null;
                console.error("Websocket init failed:", e);
                if (!cancelled) setError(e?.message ?? "WS init failed");
            }
        })();

        return () => {
            cancelled = true;
        };
        // Intentionally run once:
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const cleanup = useCallback(async () => {
        try {
            workletNodeRef.current?.disconnect();
            workletNodeRef.current = null;

            if (audioCtxRef.current) {
                await audioCtxRef.current.close();
                audioCtxRef.current = null;
            }

            if (streamRef.current) {
                streamRef.current.getTracks().forEach((t) => t.stop());
                streamRef.current = null;
            }

            if (clientRef.current && clientRef.current.isOpen()) {
                clientRef.current.sendStopRecording({ reason: "user_released" })
            }
        } finally {
            // UI: we can flip immediately, server will close shortly after END
            setIsRecording(false);
        }
    }, []);

    const startRecording = useCallback(async () => {
        if (isRecording) return;
        setTranscripts([]); // Empty the transcript history
        setError(null);
        if (clientRef.current === null) return;
        try {
            stopCurrentAudio();
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
            });
            streamRef.current = stream;

            const ctx = new AudioContext({ latencyHint: "interactive" });
            audioCtxRef.current = ctx;
            await ctx.resume();

            const workletUrl = new URL("../garvis/pcm-worklet.js", import.meta.url);
            await ctx.audioWorklet.addModule(workletUrl);

            const source = ctx.createMediaStreamSource(stream);
            const workletNode = new AudioWorkletNode(ctx, "pcm16-processor");
            workletNodeRef.current = workletNode;

            // Safari keep-alive
            const silentGain = ctx.createGain();
            silentGain.gain.value = 0;
            source.connect(workletNode);
            workletNode.connect(silentGain).connect(ctx.destination);

            // Worklet outputs 16k mono PCM16LE frames (see pcm-worklet.js below)
            clientRef.current.sendStartRecording(
                createWsStartRecordingContent("pcm16le", 16000, 1, true, "en-US")
            );

            workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
                if (clientRef.current !== null) clientRef.current.sendAudioFrame(event.data);
            };

            setIsRecording(true);
        } catch (e: any) {
            setError(e?.message ?? "Failed to start audio.");
            await cleanup();
        }
    }, [cleanup, isRecording]);

    const stopRecording = useCallback(async () => {
        if (!isRecording) return;
        await cleanup();
    }, [cleanup, isRecording]);

    return { startRecording, stopRecording, isRecording, error, transcripts, wsIsConnected, garvisIsSpeaking, stopGarvisSpeech, garvisIsThinking };

}