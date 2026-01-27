import asyncio
import json
from typing import Optional

import janus
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from google.cloud import speech

router = APIRouter()


@router.websocket("/ws/audio")
async def ws_audio(websocket: WebSocket):
    await websocket.accept()
    loop = asyncio.get_running_loop()

    # Thread-safe bridge: async (FastAPI) <-> sync (Google client)
    q: janus.Queue[Optional[bytes]] = janus.Queue()

    cfg = {
        "sample_rate": 16000,
        "language_code": "en-US",
        "channels": 1,
        "interim_results": True,
    }

    stop_event = asyncio.Event()

    async def send_json(payload: dict):
        await websocket.send_text(json.dumps(payload))

    def google_streaming_worker(loop: asyncio.AbstractEventLoop):
        """
        Runs in a thread. Pulls PCM chunks from q.sync_q and feeds Google STT.
        Sends results back to the async loop using asyncio.run_coroutine_threadsafe.
        """
        client = speech.SpeechClient()

        recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=cfg["sample_rate"],
            language_code=cfg["language_code"],
            audio_channel_count=cfg["channels"],
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=cfg["interim_results"],
        )

        def request_gen():
            # First request must carry config
            yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
            while True:
                chunk = q.sync_q.get()
                if chunk is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        try:
            responses = client.streaming_recognize(requests=request_gen())
            for resp in responses:
                for result in resp.results:
                    if not result.alternatives:
                        continue
                    text = result.alternatives[0].transcript
                    is_final = result.is_final

                    # Print the full produced transcription
                    print(text)
                    if is_final:
                        print(f"[STT FINAL] {text}")
                    else:
                        print(f"[STT PARTIAL] {text}", end="\r")

                    fut = asyncio.run_coroutine_threadsafe(
                        send_json(
                            {
                                "type": "transcript",
                                "text": text,
                                "final": is_final,
                            }
                        ),
                        loop,
                    )
                    fut.result()  # propagate errors
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                send_json({"type": "error", "message": str(e)}),
                loop,
            )
        finally:
            asyncio.run_coroutine_threadsafe(
                send_json({"type": "end"}),
                loop,
            )

    # Start the worker thread lazily after we receive "start"
    worker_task: Optional[asyncio.Task] = None
    worker_started = False

    try:
        while True:
            msg = await websocket.receive()

            if "text" in msg and msg["text"] is not None:
                try:
                    data = json.loads(msg["text"])
                except json.JSONDecodeError:
                    await send_json(
                        {"type": "error", "message": "Invalid JSON control message"}
                    )
                    continue

                mtype = data.get("type")
                if mtype == "start":
                    # read config from client (fallbacks already set)
                    cfg["sample_rate"] = int(data.get("sampleRate", cfg["sample_rate"]))
                    cfg["channels"] = int(data.get("channels", cfg["channels"]))
                    cfg["language_code"] = str(
                        data.get("languageCode", cfg["language_code"])
                    )
                    cfg["interim_results"] = bool(
                        data.get("interimResults", cfg["interim_results"])
                    )

                    if not worker_started:
                        # run blocking Google streaming in a thread
                        worker_task = asyncio.create_task(
                            asyncio.to_thread(google_streaming_worker, loop)
                        )
                        worker_started = True

                    await send_json({"type": "ack", "message": "stream started"})
                elif mtype == "stop":
                    q.async_q.put_nowait(None)
                    stop_event.set()
                    await send_json({"type": "ack", "message": "stopping"})
                    break
                else:
                    await send_json(
                        {"type": "error", "message": f"Unknown control type: {mtype}"}
                    )

            elif "bytes" in msg and msg["bytes"] is not None:
                if not worker_started:
                    await send_json(
                        {
                            "type": "error",
                            "message": "Send start message before audio bytes",
                        }
                    )
                    continue
                q.async_q.put_nowait(msg["bytes"])

            else:
                await send_json({"type": "error", "message": "Unsupported message"})
    except WebSocketDisconnect:
        # Client went away
        q.async_q.put_nowait(None)
    finally:
        # Ensure worker finishes
        try:
            q.async_q.put_nowait(None)
        except Exception:
            pass
        if worker_task:
            await worker_task
        q.close()
        await q.wait_closed()
