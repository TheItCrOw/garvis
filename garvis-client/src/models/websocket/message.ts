/* eslint-disable @typescript-eslint/no-explicit-any */

export enum WsMessageType {
    START = "start",
    STOP = "stop",
    ACK = "ack",
    TRANSCRIPT = "transcript",
    GARVIS = "garvis",
    ERROR = "error",
    END = "end",
}

export interface WsMessage<T = unknown> {
    id: string,
    type: WsMessageType;
    content: T;
}

export const isWsMessage = (v: any): v is WsMessage =>
    v && typeof v === "object" && typeof v.type === "string";

export const createWsMessage = <T>(
    type: WsMessageType,
    content: T
): WsMessage<T> => ({
    id: crypto.randomUUID(),
    type,
    content,
});
