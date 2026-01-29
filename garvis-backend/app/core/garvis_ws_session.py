import asyncio
import json
from pathlib import Path
from typing import Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState
import janus

from app.core.dto.ws_messages import (
    WsAckContent,
    WsErrorContent,
    WsGarvisContent,
    WsMessage,
    WsMessageType,
    WsStartContent,
    WsStopContent,
    WsTranscriptContent,
)
from app.services.text_to_speech_service import synthesize_speech_mp3_b64
from google.cloud import speech
from uuid import uuid4

from app.core.garvis import Garvis
from app.core.garvis_task import GarvisTask


class GarvisWebsocketSession:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self.garvis = Garvis()

        self.transcription_queue: janus.Queue[Optional[bytes]] = janus.Queue()
        self.garvis_task_queue: janus.Queue[Optional[GarvisTask]] = janus.Queue()
        self.garvis_consumer_task: Optional[asyncio.Task] = None

        self.final_transcript_parts: list[str] = []
        self.session_id = str(uuid4())

        self.started = False
        self.worker_task: Optional[asyncio.Task] = None

        self.cfg = {
            "sample_rate": 16000,
            "language_code": "en-US",
            "channels": 1,
            "interim_results": True,
        }

    async def _consume_garvis_tasks(self):
        """
        A background task that constantly fetches tasks from the garvis_task_queue and
        processed them through our Garvis agent network.
        """
        while True:
            task = await self.garvis_task_queue.async_q.get()
            if task is None:
                break

            # sequential processing of a task by garvis, one at a time, in order
            # TODO! This should be: await self.garvis.handle_task(task)
            garvis_answer = "Of course sir, just one second."

            audio_b64, mime = await asyncio.to_thread(
                synthesize_speech_mp3_b64,
                garvis_answer,
                # output_path=Path(f"audio/garvis/{self.session_id}.mp3"),
            )
            # send back to client
            await self.send_garvis_answer("Completion", garvis_answer, audio_b64, mime)

    async def send(self, msg: WsMessage):
        if self.ws.client_state != WebSocketState.CONNECTED:
            return
        await self.ws.send_text(json.dumps(msg.to_json()))

    async def send_ack(self, text: str):
        await self.send(WsMessage.create(WsMessageType.ACK, WsAckContent(text)))

    async def send_error(self, text: str):
        await self.send(WsMessage.create(WsMessageType.ERROR, WsErrorContent(text)))

    async def send_end(self):
        await self.send(WsMessage.create(WsMessageType.END, {}))

    async def send_garvis_answer(
        self,
        intent: str,
        answer: str,
        audio_base64: Optional[str],
        audio_mime_type: Optional[str],
    ):
        content = WsGarvisContent(intent, answer, audio_base64, audio_mime_type)
        await self.send(WsMessage.create(WsMessageType.GARVIS, content))

    async def handle_start(self, msg: WsMessage[WsStartContent]):
        c = msg.content
        self.cfg["sample_rate"] = c.sampleRate
        self.cfg["channels"] = c.channels
        self.cfg["language_code"] = c.languageCode
        self.cfg["interim_results"] = c.interimResults

        if self.garvis_consumer_task is None:
            self.garvis_consumer_task = asyncio.create_task(
                self._consume_garvis_tasks()
            )

        if not self.started:
            self.worker_task = asyncio.create_task(
                asyncio.to_thread(self._stt_worker, self.loop)
            )
            self.started = True

        await self.send_ack("stream started")

    async def handle_stop(self, msg: WsMessage[WsStopContent]):
        # signal generator to end
        try:
            self.transcription_queue.async_q.put_nowait(None)
        except Exception:
            pass

        await self.send_ack("stopping")
        # IMPORTANT: wait for worker to flush final transcripts
        if self.worker_task:
            await self.worker_task

        # stop garvis consumer
        self.garvis_task_queue.sync_q.put(None)
        if self.garvis_consumer_task:
            await self.garvis_consumer_task

        full_transcription_history = " ".join(self.final_transcript_parts)
        print(full_transcription_history)

        # After everything finishes, send END
        await self.send_end()

    async def handle_audio(self, data: bytes):
        if not self.started:
            await self.send_error("Send START before audio bytes")
            return
        self.transcription_queue.async_q.put_nowait(data)

    def _stt_worker(self, loop: asyncio.AbstractEventLoop):
        client = speech.SpeechClient()

        recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.cfg["sample_rate"],
            language_code=self.cfg["language_code"],
            audio_channel_count=self.cfg["channels"],
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=self.cfg["interim_results"],
        )

        def request_gen():
            while True:
                chunk = self.transcription_queue.sync_q.get()
                if chunk is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        try:
            responses = client.streaming_recognize(
                config=streaming_config, requests=request_gen()
            )

            for resp in responses:
                for result in resp.results:
                    if not result.alternatives:
                        continue
                    text = result.alternatives[0].transcript
                    is_final = result.is_final

                    if is_final:
                        self.final_transcript_parts.append(text)
                        self.garvis_task_queue.sync_q.put(
                            GarvisTask(self.session_id, text)
                        )
                        print("Adding task to garvis queue:", text)
                        print(
                            "Task-Q size:",
                            self.garvis_task_queue.sync_q.qsize(),
                            flush=True,
                        )
                    print(f"[{'FINAL' if is_final else 'INTERIM'}] {text}", flush=True)

                    asyncio.run_coroutine_threadsafe(
                        self.send(
                            WsMessage.create(
                                WsMessageType.TRANSCRIPT,
                                WsTranscriptContent(text=text, final=is_final),
                            )
                        ),
                        loop,
                    ).result()

        except Exception as e:
            print("GOOGLE ERROR:", str(e), flush=True)
            asyncio.run_coroutine_threadsafe(self.send_error(str(e)), loop)
        # NOTE: END is emitted by handle_stop(), not here (prevents send-after-close races)
