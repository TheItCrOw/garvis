import asyncio
import json
from typing import Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState
import janus

from app.core.dto.ws_messages import (
    WsAckContent,
    WsErrorContent,
    WsMessage,
    WsMessageType,
    WsStartContent,
    WsStopContent,
    WsTranscriptContent,
)
from google.cloud import speech


class GarvisWsSession:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self.q: janus.Queue[Optional[bytes]] = janus.Queue()
        self.final_transcript_parts: list[str] = []

        self.started = False
        self.worker_task: Optional[asyncio.Task] = None

        self.cfg = {
            "sample_rate": 16000,
            "language_code": "en-US",
            "channels": 1,
            "interim_results": True,
        }

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

    async def send_garvis_answer(self, garvis_answer):
        await self.send(WsMessage.create(WsMessageType.GARVIS, {}))

    async def handle_start(self, msg: WsMessage[WsStartContent]):
        c = msg.content
        self.cfg["sample_rate"] = c.sampleRate
        self.cfg["channels"] = c.channels
        self.cfg["language_code"] = c.languageCode
        self.cfg["interim_results"] = c.interimResults

        if not self.started:
            self.worker_task = asyncio.create_task(
                asyncio.to_thread(self._google_worker, self.loop)
            )
            self.started = True

        await self.send_ack("stream started")

    async def handle_stop(self, msg: WsMessage[WsStopContent]):
        # signal generator to end
        try:
            self.q.async_q.put_nowait(None)
        except Exception:
            pass

        await self.send_ack("stopping")

        # IMPORTANT: wait for worker to flush final transcripts
        if self.worker_task:
            await self.worker_task

        # TODO @Brando: Here we have the full transcript.
        # This is the entry point into the agent network.
        transcription = " ".join(self.final_transcript_parts)
        print(transcription)
        garvis_answer = None  # I'll have to think about the exact return format
        await self.send_garvis_answer(garvis_answer)

        # After agents finish, send END
        await self.send_end()

    async def handle_audio(self, data: bytes):
        if not self.started:
            await self.send_error("Send START before audio bytes")
            return
        self.q.async_q.put_nowait(data)

    def _google_worker(self, loop: asyncio.AbstractEventLoop):
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
                chunk = self.q.sync_q.get()
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
