// pcm-worklet.js
// Resample from input sampleRate -> 16000 Hz using linear interpolation
// Batch into 20ms frames: 320 samples at 16k, mono, PCM16LE.
// every message from the worklet is exactly 20ms, 16kHz, mono, PCM16LE.

class Pcm16ResampleProcessor extends AudioWorkletProcessor {
    constructor() {
        super();

        this.targetRate = 16000;
        this.frameSamples = 320; // 20ms @ 16k

        // Resampling state
        this._ratio = sampleRate / this.targetRate; // inputRate / targetRate
        this._t = 0; // fractional read index into input stream

        // Keep last sample for interpolation across blocks
        this._prev = 0;

        // Output batching
        this._out = new Int16Array(this.frameSamples);
        this._outIndex = 0;
    }

    _floatToInt16(x) {
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

        // We treat the input as a continuous stream:
        // previous block last sample is at index -1 (this._prev),
        // current block samples are at indices [0..n-1].
        // this._t is the "time" in input-sample units.

        while (true) {
            // Need input sample at floor(t) and floor(t)+1
            const i0 = Math.floor(this._t);
            const i1 = i0 + 1;

            // If i0 is beyond current block, stop until next process() call.
            if (i0 >= n) {
                // Carry leftover fractional position into next block
                this._t -= n;
                // Update prev to last sample of this block for next interpolation
                this._prev = inBuf[n - 1] ?? this._prev;
                break;
            }

            const s0 = i0 === -1 ? this._prev : inBuf[i0];
            const s1 =
                i1 === -1 ? this._prev : i1 < n ? inBuf[i1] : inBuf[n - 1] ?? this._prev;

            const frac = this._t - i0;
            const sample = s0 + (s1 - s0) * frac;

            // Write to output frame
            this._out[this._outIndex++] = this._floatToInt16(sample);

            if (this._outIndex === this.frameSamples) {
                // Send 20ms frame
                const ab = this._out.buffer;
                this.port.postMessage(ab, [ab]);
                this._out = new Int16Array(this.frameSamples);
                this._outIndex = 0;
            }

            // Advance in input time by ratio
            this._t += this._ratio;
        }

        return true;
    }
}

registerProcessor("pcm16-processor", Pcm16ResampleProcessor);
