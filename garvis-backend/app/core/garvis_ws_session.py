import asyncio
from datetime import datetime
import json
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
    WsStartRecordingContent,
    WsStopRecordingContent,
    WsTranscriptContent,
)
from app.services.text_to_speech_service import TextToSpeechService
from app.database.duckdb_data_service import data_service
from google.cloud import speech
from uuid import uuid4

from app.core.garvis import get_garvis
from app.core.dto.garvis_dtos import GarvisTask, GarvisReply
from app.utils.date_utils import get_day_info
from app.utils.string_utils import normalize_text


class GarvisWebsocketSession:
    def __init__(
        self,
        websocket: WebSocket,
        tts_service: TextToSpeechService,
        stt_client: speech.SpeechClient,
    ):
        self.ws = websocket
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self.ds = data_service
        self.garvis = get_garvis()

        self.transcription_queue: janus.Queue[Optional[bytes]] = janus.Queue()
        self.garvis_task_queue: janus.Queue[Optional[GarvisTask]] = janus.Queue()
        self.garvis_consumer_task: Optional[asyncio.Task] = None

        self.final_transcript_parts: list[str] = []
        self.session_id = str(uuid4())

        self.isRecording = False
        self.worker_task: Optional[asyncio.Task] = None

        self.cfg = {
            "sample_rate": 16000,
            "language_code": "en-US",
            "channels": 1,
            "interim_results": True,
        }

        # Create the text-to-speech service
        self.tts_service = tts_service

        # Create the speech-to-text Google Cloud connection clients
        self.stt_client = stt_client
        self.stt_recognition_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.cfg["sample_rate"],
            language_code=self.cfg["language_code"],
            audio_channel_count=self.cfg["channels"],
        )
        self.stt_streaming_config = speech.StreamingRecognitionConfig(
            config=self.stt_recognition_config,
            interim_results=self.cfg["interim_results"],
        )

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

    async def send_welcome_message(self):
        now = datetime.now()
        day = get_day_info(now)
        hour = now.strftime("%I").lstrip("0")
        am_pm = now.strftime("%p").lower()
        message = f"Welcome Sir, it's {day.weekday} the {day.day} of {day.month}, {hour} o'clock {am_pm}"
        audio_b64, mime = await asyncio.to_thread(
            self.tts_service.synthesize_speech_mp3_b64, message
        )
        await self.send_garvis_answer(
            "Welcome",
            GarvisReply("", "Say your welcome Garvis!", message),
            audio_b64,
            mime,
        )

    async def send_garvis_answer(
        self,
        intent: str,
        garvis_reply: GarvisReply,
        audio_base64: str,
        audio_mime_type: str,
    ):
        content = WsGarvisContent(
            intent,
            user_query=garvis_reply.query,
            answer=garvis_reply.reply,
            audio_base64=audio_base64,
            audio_mime_type=audio_mime_type,
            open_view=garvis_reply.view,
            action=garvis_reply.action,
            parameters=garvis_reply.parameters,
            intent_confidence=garvis_reply.intent_confidence,
        )
        await self.send(WsMessage.create(WsMessageType.GARVIS, content))

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
            garvis_reply = await self.garvis.handle_task(task)
            audio_b64, mime = await asyncio.to_thread(
                self.tts_service.synthesize_speech_mp3_b64,
                garvis_reply.reply,
            )
            # send back to client
            await self.send_garvis_answer("Completion", garvis_reply, audio_b64, mime)

    async def handle_start_recording(self, msg: WsMessage[WsStartRecordingContent]):
        c = msg.content
        self.cfg["sample_rate"] = c.sampleRate
        self.cfg["channels"] = c.channels
        self.cfg["language_code"] = c.languageCode
        self.cfg["interim_results"] = c.interimResults

        # if self.garvis_consumer_task is None:
        self.garvis_consumer_task = asyncio.create_task(self._consume_garvis_tasks())

        if not self.isRecording:
            self.worker_task = asyncio.create_task(
                asyncio.to_thread(self._stt_worker, self.loop)
            )
            self.isRecording = True

        await self.send_ack("audio stream started")
        print("Starting recording.")

    async def handle_stop_recording(self, msg: WsMessage[WsStopRecordingContent]):
        # signal generator to end
        try:
            self.transcription_queue.async_q.put_nowait(None)
        except Exception:
            pass

        print("Stopping recording.")
        await self.send_ack("stopping recording")
        # IMPORTANT: wait for worker to flush final transcripts
        if self.worker_task:
            await self.worker_task

        # stop garvis consumer
        self.garvis_task_queue.sync_q.put(None)
        if self.garvis_consumer_task:
            await self.garvis_consumer_task

        self.isRecording = False
        full_transcription_history = " ".join(self.final_transcript_parts)
        print(full_transcription_history)

    async def handle_audio(self, data: bytes):
        if not self.isRecording:
            await self.send_error("Send START before audio bytes")
            return
        self.transcription_queue.async_q.put_nowait(data)

    def _stt_worker(self, loop: asyncio.AbstractEventLoop):

        def request_gen():
            while True:
                chunk = self.transcription_queue.sync_q.get()
                if chunk is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        try:
            responses = self.stt_client.streaming_recognize(
                config=self.stt_streaming_config, requests=request_gen()
            )

            for resp in responses:
                for result in resp.results:
                    if not result.alternatives:
                        continue
                    text = result.alternatives[0].transcript
                    is_final = result.is_final
                    if is_final:
                        text = normalize_text(text)

                    asyncio.run_coroutine_threadsafe(
                        self.send(
                            WsMessage.create(
                                WsMessageType.TRANSCRIPT,
                                WsTranscriptContent(text=text, final=is_final),
                            )
                        ),
                        loop,
                    ).result()

                    if is_final:
                        if text is not None and len(text) > 2:
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

        except Exception as e:
            print("GOOGLE ERROR:", str(e), flush=True)
            asyncio.run_coroutine_threadsafe(self.send_error(str(e)), loop)
