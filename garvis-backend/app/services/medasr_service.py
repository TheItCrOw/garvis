import os
import sys
import io
import dataclasses
from transformers import pipeline, AutoTokenizer
from transformers import LasrFeatureExtractor
from huggingface_hub import hf_hub_download

import soundfile as sf
import pyctcdecode


def _restore_text(text: str) -> str:
    return text.replace(" ", "").replace("#", " ").replace("</s>", "").strip()


class LasrCtcBeamSearchDecoder:
    def __init__(self, tokenizer, kenlm_model_path):
        vocab = [None for _ in range(tokenizer.vocab_size)]
        for k, v in tokenizer.vocab.items():
            if v < tokenizer.vocab_size:
                vocab[v] = k

        vocab[0] = ""  # blank token

        for i in range(1, len(vocab)):
            piece = vocab[i]
            if not piece.startswith("<") and not piece.endswith(">"):
                piece = "▁" + piece.replace("▁", "#")
            vocab[i] = piece

        self._decoder = pyctcdecode.build_ctcdecoder(vocab, kenlm_model_path)

    def decode_beams(self, *args, **kwargs):
        beams = self._decoder.decode_beams(*args, **kwargs)
        return [dataclasses.replace(i, text=_restore_text(i.text)) for i in beams]


class MedASR:
    """
    MedASR service WITH KenLM language model:
    https://developers.google.com/health-ai-developer-foundations/medasr.
    Loads once per process.
    """

    _pipe = None

    def __init__(self, model_id="google/medasr"):
        self.model_id = model_id
        self.hf_token = os.environ.get("HF_TOKEN")

    def _get_pipe(self):
        if MedASR._pipe is None:
            # download LM file
            lm_path = hf_hub_download(
                self.model_id,
                filename="lm_6.kenlm",
                token=self.hf_token,
            )

            feature_extractor = LasrFeatureExtractor.from_pretrained(
                self.model_id,
                token=self.hf_token,
            )
            feature_extractor._processor_class = "LasrProcessorWithLM"

            decoder = LasrCtcBeamSearchDecoder(
                AutoTokenizer.from_pretrained(
                    self.model_id,
                    token=self.hf_token,
                ),
                lm_path,
            )

            MedASR._pipe = pipeline(
                task="automatic-speech-recognition",
                model=self.model_id,
                feature_extractor=feature_extractor,
                decoder=decoder,
                token=self.hf_token,
            )

        return MedASR._pipe

    def transcribe_from_path(self, audio_path: str):
        pipe = self._get_pipe()
        return pipe(
            audio_path,
            chunk_length_s=20,
            stride_length_s=2,
            decoder_kwargs={"beam_width": 8},
        )

    def transcribe_audio(self, audio_bytes: bytes):
        if sf is None:
            raise RuntimeError("Install soundfile: pip install soundfile")

        pipe = self._get_pipe()

        data, samplerate = sf.read(io.BytesIO(audio_bytes))
        audio_input = {
            "array": data,
            "sampling_rate": samplerate,
        }

        return pipe(
            audio_input,
            chunk_length_s=20,
            stride_length_s=2,
            decoder_kwargs={"beam_width": 8},
        )


def test():
    audio_path = "./audio/garvis/5ded15f5-e361-445f-8f21-0bc36aa4b540.mp3"

    svc = MedASR()
    result = svc.transcribe_from_path(audio_path)

    print("=== TEXT ===")
    print(result["text"])


if __name__ == "__main__":
    # Usage from root folder:
    #   python app\services\medasr_service.py
    test()
