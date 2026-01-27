from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.api.health import router as health_router
from app.database.duckdb_data_service import DataService
from contextlib import asynccontextmanager
from app.api.speech_to_text import router as stt_router

load_dotenv()

app = FastAPI(title="Garvis Backend", version="0.1.0")
app.include_router(stt_router)

############################ From Kevin ##############################
app.include_router(health_router, prefix="/api")
ds = DataService()
print("Total Patients", ds.count_patients())


@app.get("/")
def root():
    return {"name": "garvis-backend", "status": "ok"}


######################################################################
