/* eslint-disable @typescript-eslint/no-explicit-any */

export enum WsMessageType {
    START_RECORDING = "startRecording",
    STOP_RECORDING = "stopRecording",
    ACK = "ack",
    TRANSCRIPT = "transcript",
    GARVIS = "garvis",
    ERROR = "error",
    END = "end",
}

export interface WsMessage<T = unknown> {
    id: string;
    type: WsMessageType;
    content: T;
}

export const isWsMessage = (v: any): v is WsMessage =>
    v && typeof v === "object" && typeof v.type === "string" && typeof v.id === "string";

export const createWsMessage = <T>(type: WsMessageType, content: T): WsMessage<T> => ({
    id: crypto.randomUUID(),
    type,
    content,
});

// ---- Message Contents ----

export interface WsStartRecordingContent {
    format: string;
    sampleRate: number;
    channels: number;
    interimResults: boolean;
    languageCode: string;
}

export const createWsStartRecordingContent = (
    format: string,
    sampleRate: number,
    channels: number,
    interimResults: boolean,
    languageCode: string
): WsStartRecordingContent => ({
    format,
    sampleRate,
    channels,
    interimResults,
    languageCode,
});

export interface WsGarvisContent {
    intent: string;
    answer: string;
    audio_base64?: string;
    audio_mime_type?: string;
}

export interface WsStopRecordingContent {
    reason?: string;
}

export interface WsAckContent {
    message: string;
}

export interface WsTranscriptContent {
    text: string;
    final: boolean;
}

export interface WsErrorContent {
    message: string;
}
