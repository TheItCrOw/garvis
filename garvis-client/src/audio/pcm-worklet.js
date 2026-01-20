
class Pcm16Processor extends AudioWorkletProcessor {
    process(inputs) {
        const input = inputs[0];
        if (!input || input.length === 0) return true;

        // Mono: take channel 0
        const channel = input[0];
        if (!channel) return true;

        // Convert Float32 [-1, 1] -> Int16
        const pcm16 = new Int16Array(channel.length);
        for (let i = 0; i < channel.length; i++) {
            let s = channel[i];
            s = Math.max(-1, Math.min(1, s));
            pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        // Send as transferable ArrayBuffer for efficiency
        this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
        return true;
    }
}

registerProcessor("pcm16-processor", Pcm16Processor);
