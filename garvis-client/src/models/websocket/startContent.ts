
export interface WsStartContent {
    format: string,
    sampleRate: number,
    channels: number,
    interimResults: boolean,
    languageCode: string
}

export const createWsStartContent = (
    format: string,
    sampleRate: number,
    channels: number,
    interimResults: boolean,
    languageCode: string
): WsStartContent => ({
    format,
    sampleRate,
    channels,
    interimResults,
    languageCode
});
