import asyncio
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Response
from app.api.ws_garvis_router import tts_service
from app.core.dto.garvis_dtos import GarvisTask
from app.core.dto.ws_messages import WsGarvisContent, WsMessage
from app.core.garvis import get_garvis
from app.database.duckdb_data_service import data_service

router = APIRouter()


@router.get("/xrays/{xray_id}/image")
def get_xray_image(xray_id: int):
    try:
        data, mime = data_service.load_xray_image_bytes(xray_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="XRAY not found")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image file missing")

    return Response(
        content=data,
        media_type=mime,
        headers={
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/xrays/{xray_id}/garvis_analyze")
async def analyze_xray_image(xray_id: int, session_id: str | None = None):
    try:
        data, mime = data_service.load_xray_image_as_base64(xray_id, downsample=True)
    except KeyError:
        raise HTTPException(status_code=404, detail="XRAY not found")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image file missing")

    if session_id is None:
        session_id = str(uuid4())
    task = GarvisTask(
        session_id=session_id,
        query="As a medical expert, analyze the following medical-related image of an XRAY or CT scan by looking for anomalies and give a brief rundown.",
        base64_image=data,
    )

    reply = await get_garvis().handle_task(task)
    audio_b64, mime = await asyncio.to_thread(
        tts_service.synthesize_speech_mp3_b64,
        reply.reply,
    )
    garvis_content = WsGarvisContent(
        "XRAY-Analysis",
        user_query=task.query,
        answer=reply.reply,
        audio_base64=audio_b64,
        audio_mime_type=mime,
        open_view="xray",
        action="open",
        parameters=xray_id,
        intent_confidence=1,
    )
    return garvis_content
