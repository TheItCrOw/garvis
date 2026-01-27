/* eslint-disable @typescript-eslint/no-explicit-any */
import { useCallback, useRef, useState } from "react";
import { createWsMessage, WsMessageType } from "../models/websocket/message";
import { createWsStartContent } from "../models/websocket/startContent";

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
            // 1) Get mic permission + stream
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            streamRef.current = stream;

            // 2) AudioContext (must be started from a user gesture on iOS)
            const ctx = new AudioContext({ latencyHint: "interactive" });
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
                console.log("[WS] open");
                const startMsg = createWsMessage(
                    WsMessageType.START,
                    createWsStartContent("pcm16le", 16000, 1, true, "en-US")
                )
                ws.send(JSON.stringify(startMsg));

                let frames = 0;

                workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
                    frames++;
                    if (frames % 50 === 0) {
                        console.log("[AUDIO] sending frame", frames, "bytes=", event.data.byteLength);
                    }
                    if (ws.readyState === WebSocket.OPEN) ws.send(event.data);
                };

                setIsRecording(true);
            };

            ws.onmessage = (ev) => {
                if (typeof ev.data !== "string") return;
                const msg = JSON.parse(ev.data);

                if (msg.type === "transcript") {
                    console.log(`[${msg.final ? "FINAL" : "INTERIM"}] ${msg.text}`);
                }

                if (msg.type === "end") {
                    console.log("[WS] end from server, closing socket");
                    ws.close();
                }
            };

            ws.onerror = (e) => {
                console.log("[WS] error", e);
                setError("WebSocket error.");
            };

            ws.onclose = (e) => {
                console.log("[WS] close", { code: e.code, reason: e.reason, wasClean: e.wasClean });
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
