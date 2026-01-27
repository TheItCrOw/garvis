"""
Module to establish a speech-to-text route for the server.
We're using Google's Cloud Speech-to-Text API:
https://console.cloud.google.com/apis/api/speech.googleapis.com/metrics?project=kaggle-medgemma-hackathon-2026
"""

import asyncio
import json
from typing import Optional

import janus
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.log_utils import log_message
from app.utils.websocket_utils import WebsocketMessenger
from google.cloud import speech

router = APIRouter()

SAMPLING_CFG = {
    "sample_rate": 16000,
    "language_code": "en-US",
    "channels": 1,
    "interim_results": True,
}


def google_streaming_worker(
    loop: asyncio.AbstractEventLoop, q: janus.Queue, messenger: WebsocketMessenger
):
    """
    The background worker thread that continuously does transcriptions based on
    audio chunks by querying a Google SST model.
    """
    client = speech.SpeechClient()

    recognition_config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLING_CFG["sample_rate"],
        language_code=SAMPLING_CFG["language_code"],
        audio_channel_count=SAMPLING_CFG["channels"],
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=recognition_config,
        interim_results=SAMPLING_CFG["interim_results"],
    )

    def request_gen():
        while True:
            chunk = q.sync_q.get()
            if chunk is None:
                break
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    try:
        responses = client.streaming_recognize(
            config=streaming_config,
            requests=request_gen(),
        )

        for resp in responses:
            for result in resp.results:
                if not result.alternatives:
                    continue
                text = result.alternatives[0].transcript
                is_final = result.is_final

                print(f"[{'FINAL' if is_final else 'INTERIM'}] {text}", flush=True)

                fut = asyncio.run_coroutine_threadsafe(
                    messenger.send_json(
                        {"type": "transcript", "text": text, "final": is_final}
                    ),
                    loop,
                )
                fut.result()

    except Exception as e:
        print("GOOGLE ERROR:", str(e), flush=True)
        asyncio.run_coroutine_threadsafe(
            messenger.send_json({"type": "error", "message": str(e)}),
            loop,
        )
    finally:
        asyncio.run_coroutine_threadsafe(messenger.send_json({"type": "end"}), loop)


@router.websocket("/ws/audio")
async def ws_audio(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()
    messenger = WebsocketMessenger(websocket)
    q: janus.Queue[Optional[bytes]] = janus.Queue()

    worker_task: Optional[asyncio.Task] = None
    worker_started = False

    try:
        while True:
            msg = await websocket.receive()

            # Control messages
            if msg.get("text") is not None:
                try:
                    data = json.loads(msg["text"])
                except json.JSONDecodeError:
                    await messenger.send_json(
                        {"type": "error", "message": "Invalid JSON control message"}
                    )
                    continue

                mtype = data.get("type")

                if mtype == "start":
                    # If the client sends us the "start" type, we init the transcription queue
                    SAMPLING_CFG["sample_rate"] = int(
                        data.get("sampleRate", SAMPLING_CFG["sample_rate"])
                    )
                    SAMPLING_CFG["channels"] = int(
                        data.get("channels", SAMPLING_CFG["channels"])
                    )
                    SAMPLING_CFG["language_code"] = str(
                        data.get("languageCode", SAMPLING_CFG["language_code"])
                    )
                    SAMPLING_CFG["interim_results"] = bool(
                        data.get("interimResults", SAMPLING_CFG["interim_results"])
                    )

                    if not worker_started:
                        worker_task = asyncio.create_task(
                            asyncio.to_thread(
                                google_streaming_worker, loop, q, messenger
                            )
                        )
                        worker_started = True

                    await messenger.send_json(
                        {"type": "ack", "message": "stream started"}
                    )

                elif mtype == "stop":
                    # If the client tells us stop, the audio recording has stopped. In that case
                    # we finish the transcription and send back the final response.
                    q.async_q.put_nowait(None)
                    await messenger.send_json({"type": "ack", "message": "stopping"})

                    # Wait for Google worker to finish sending final transcripts, then only end
                    if worker_task:
                        await worker_task
                    break

                else:
                    # In all other cases, something went wrong.
                    await messenger.send_json(
                        {"type": "error", "message": f"Unknown control type: {mtype}"}
                    )

            # Here we handle Audio bytes chunks sent by the client
            elif (
                msg.get("bytes") is not None
            ):  # You cannot expect to transcribe if you haven't send a "start"
                # message yet before.
                if not worker_started:
                    await messenger.send_json(
                        {
                            "type": "error",
                            "message": "Send start message before audio bytes",
                        }
                    )
                    continue
                # Let's put the audio chunks to the queue and let the background worker handle them.
                q.async_q.put_nowait(msg["bytes"])

            else:
                await messenger.send_json(
                    {"type": "error", "message": "Unsupported message"}
                )

    except WebSocketDisconnect:
        pass
    finally:
        # signal worker to stop
        try:
            q.async_q.put_nowait(None)
        except Exception:
            pass

        if worker_task:
            await worker_task

        q.close()
        await q.wait_closed()
