/* eslint-disable @typescript-eslint/no-explicit-any */
import {
    type WsMessage,
    WsMessageType,
    createWsMessage,
    isWsMessage,
    type WsStartContent,
    type WsStopContent,
    type WsTranscriptContent,
    type WsAckContent,
    type WsErrorContent,
    type WsGarvisContent,
} from "../models/websocket/messages"

type Listener<T> = (msg: WsMessage<T>) => void;

export class GarvisWsClient {
    private ws: WebSocket | null = null;

    private onAckListeners: Listener<WsAckContent>[] = [];
    private onTranscriptListeners: Listener<WsTranscriptContent>[] = [];
    private onGarvisListeners: Listener<WsGarvisContent>[] = [];
    private onErrorListeners: Listener<WsErrorContent>[] = [];
    private onEndListeners: Listener<unknown>[] = [];
    private onRawMessageListeners: ((raw: unknown) => void)[] = [];

    constructor(private readonly url: string) { }

    connect(): Promise<void> {
        if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
            return Promise.resolve();
        }

        return new Promise((resolve, reject) => {
            const ws = new WebSocket(this.url);
            ws.binaryType = "arraybuffer";
            this.ws = ws;

            ws.onopen = () => resolve();
            ws.onerror = () => reject(new Error("WebSocket error"));

            ws.onmessage = (ev) => {
                // backend only sends JSON text. If its something else, skip it.
                if (typeof ev.data !== "string") return;

                try {
                    const parsed = JSON.parse(ev.data);
                    this.onRawMessageListeners.forEach((fn) => fn(parsed));

                    if (!isWsMessage(parsed)) return;

                    const msg = parsed as WsMessage<any>;
                    switch (msg.type) {
                        case WsMessageType.ACK:
                            this.onAckListeners.forEach((fn) => fn(msg as WsMessage<WsAckContent>));
                            break;
                        case WsMessageType.TRANSCRIPT:
                            this.onTranscriptListeners.forEach((fn) => fn(msg as WsMessage<WsTranscriptContent>));
                            break;
                        case WsMessageType.ERROR:
                            this.onErrorListeners.forEach((fn) => fn(msg as WsMessage<WsErrorContent>));
                            break;
                        case WsMessageType.GARVIS:
                            this.onGarvisListeners.forEach((fn) => fn(msg as WsMessage<WsGarvisContent>));
                            break;
                        case WsMessageType.END:
                            this.onEndListeners.forEach((fn) => fn(msg));
                            break;
                        default:
                            // ignore or add more handlers later
                            break;
                    }
                } catch {
                    // ignore invalid JSON
                }
            };

            ws.onclose = () => {
                // no-op; consumers can listen to END/ERROR
            };
        });
    }

    isOpen(): boolean {
        return !!this.ws && this.ws.readyState === WebSocket.OPEN;
    }

    send<T>(msg: WsMessage<T>): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        this.ws.send(JSON.stringify(msg));
    }

    sendStart(content: WsStartContent): void {
        this.send(createWsMessage(WsMessageType.START, content));
    }

    sendStop(content: WsStopContent = {}): void {
        this.send(createWsMessage(WsMessageType.STOP, content));
    }

    sendAudioFrame(buffer: ArrayBuffer): void {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        this.ws.send(buffer);
    }

    close(): void {
        if (!this.ws) return;
        // let server close too; but allow manual close
        this.ws.close();
        this.ws = null;
    }

    // --- subscriptions ---
    onAck(fn: Listener<WsAckContent>): () => void {
        this.onAckListeners.push(fn);
        return () => (this.onAckListeners = this.onAckListeners.filter((x) => x !== fn));
    }

    onTranscript(fn: Listener<WsTranscriptContent>): () => void {
        this.onTranscriptListeners.push(fn);
        return () => (this.onTranscriptListeners = this.onTranscriptListeners.filter((x) => x !== fn));
    }

    onGarvis(fn: Listener<WsGarvisContent>): () => void {
        this.onGarvisListeners.push(fn);
        return () => (this.onGarvisListeners = this.onGarvisListeners.filter((x) => x !== fn));
    }

    onError(fn: Listener<WsErrorContent>): () => void {
        this.onErrorListeners.push(fn);
        return () => (this.onErrorListeners = this.onErrorListeners.filter((x) => x !== fn));
    }

    onEnd(fn: Listener<unknown>): () => void {
        this.onEndListeners.push(fn);
        return () => (this.onEndListeners = this.onEndListeners.filter((x) => x !== fn));
    }

    onRawMessage(fn: (raw: unknown) => void): () => void {
        this.onRawMessageListeners.push(fn);
        return () => (this.onRawMessageListeners = this.onRawMessageListeners.filter((x) => x !== fn));
    }
}
