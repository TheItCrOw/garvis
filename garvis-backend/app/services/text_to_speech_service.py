from pathlib import Path
from typing import Optional, Tuple
import base64

from google.cloud import texttospeech


def synthesize_speech_mp3_b64(
    text: str,
    *,
    voice_name: str = "en-US-Chirp3-HD-Umbriel",
    language_code: str = "en-US",
    output_path: Optional[Path] = None,
) -> Tuple[str, str]:
    """
    Synthesize speech using Google TTS (Chirp3 HD).
    Returns base64 audio + mime type.
    Optionally writes MP3 to disk.
    """
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )

    audio_bytes = response.audio_content

    # write file if requested
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(audio_bytes)

    # encode for WS transport
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
    return audio_b64, "audio/mpeg"
