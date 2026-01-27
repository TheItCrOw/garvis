import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.garvis_ws_session import GarvisWsSession
from app.core.dto.ws_messages import (
    WsMessage,
    WsMessageType,
    WsStartContent,
    WsStopContent,
)

router = APIRouter()


@router.websocket("/ws/audio")
async def ws_audio(websocket: WebSocket):
    await websocket.accept()
    session = GarvisWsSession(websocket)

    try:
        while True:
            msg = await websocket.receive()

            if msg.get("text") is not None:
                try:
                    raw = json.loads(msg["text"])
                except json.JSONDecodeError:
                    await session.send_error("Invalid JSON")
                    continue

                # route by type
                try:
                    message_type = WsMessageType(raw.get("type"))
                except Exception:
                    await session.send_error("Unknown message type")
                    continue

                if message_type == WsMessageType.START:
                    parsed = WsMessage.from_json(raw, content_cls=WsStartContent)
                    await session.handle_start(parsed)
                elif message_type == WsMessageType.STOP:
                    parsed = WsMessage.from_json(raw, content_cls=WsStopContent)
                    await session.handle_stop(parsed)
                    break
                else:
                    await session.send_error(
                        f"Unsupported control message: {message_type.value}"
                    )

            elif msg.get("bytes") is not None:
                await session.handle_audio(msg["bytes"])
            else:
                await session.send_error("Unsupported message")

    except WebSocketDisconnect:
        # client vanished: stop worker
        try:
            session.transcription_queue.async_q.put_nowait(None)
            session.garvis_task_queue.async_q.put_nowait(None)
        except Exception:
            pass
        if session.worker_task:
            await session.worker_task
    finally:
        session.transcription_queue.close()
        session.garvis_task_queue.close()
        await session.transcription_queue.wait_closed()
        await session.garvis_task_queue.wait_closed()
