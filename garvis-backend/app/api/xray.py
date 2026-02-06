from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

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
