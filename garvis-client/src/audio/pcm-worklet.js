// pcm-worklet.js
// Resample from input sampleRate -> 16000 Hz using linear interpolation
// Batch into 20ms frames: 320 samples at 16k, mono, PCM16LE.
// every message from the worklet is exactly 20ms, 16kHz, mono, PCM16LE.

class Pcm16ResampleProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.targetRate = 16000;
        this.frameSamples = 320;

        this._ratio = sampleRate / this.targetRate;
        this._t = 0;
        this._prev = 0;

        this._out = new Int16Array(this.frameSamples);
        this._outIndex = 0;
    }

    _f32ToI16(x) {
        const s = Math.max(-1, Math.min(1, x));
        return s < 0 ? (s * 0x8000) | 0 : (s * 0x7fff) | 0;
    }

    process(inputs) {
        const input = inputs[0];
        if (!input || input.length === 0) return true;

        const ch0 = input[0];
        if (!ch0) return true;

        const inBuf = ch0;
        const n = inBuf.length;

        while (true) {
            const i0 = Math.floor(this._t);
            const i1 = i0 + 1;

            if (i0 >= n) {
                this._t -= n;
                this._prev = inBuf[n - 1] ?? this._prev;
                break;
            }

            const s0 = i0 === -1 ? this._prev : inBuf[i0];
            const s1 =
                i1 === -1 ? this._prev : i1 < n ? inBuf[i1] : inBuf[n - 1] ?? this._prev;

            const frac = this._t - i0;
            const sample = s0 + (s1 - s0) * frac;

            this._out[this._outIndex++] = this._f32ToI16(sample);

            if (this._outIndex === this.frameSamples) {
                const ab = this._out.buffer;
                this.port.postMessage(ab, [ab]);
                this._out = new Int16Array(this.frameSamples);
                this._outIndex = 0;
            }

            this._t += this._ratio;
        }

        return true;
    }
}

registerProcessor("pcm16-processor", Pcm16ResampleProcessor);