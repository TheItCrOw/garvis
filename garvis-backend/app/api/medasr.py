# medasr.py

import os
import shutil
import tempfile

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.services.medasr_service import MedASR, test as test_medasr

router = APIRouter(prefix="/medasr", tags=["medasr"])
print("Setting up and testing the MedASR service...")
medasr = MedASR()
test_medasr()


@router.post("/transcribe")
async def transcribe_medical_audio(uploaded_file: UploadFile = File(...)):
    """
    Accepts an uploaded audio file and returns MedASR transcription.
    Client should send multipart/form-data with field name: uploaded_file
    """
    temp_file_path = None

    try:
        suffix = os.path.splitext(uploaded_file.filename or "")[1] or ".wav"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            uploaded_file.file.seek(0)
            shutil.copyfileobj(uploaded_file.file, temp_file)
            temp_file_path = temp_file.name

        result = medasr.transcribe_from_path(temp_file_path)

        return {
            "message": "Transcription created successfully",
            "filename": uploaded_file.filename,
            "text": result.get("text", ""),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
