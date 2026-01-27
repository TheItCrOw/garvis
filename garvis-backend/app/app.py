from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from app.api.health import router as health_router
from app.database.duckdb_data_service import DataService
from contextlib import asynccontextmanager
from app.api.ws_garvis_router import router as ws_garvis_router

load_dotenv()

app = FastAPI(title="Garvis Backend", version="0.1.0")
app.include_router(ws_garvis_router)

app.include_router(health_router, prefix="/api")
ds = DataService()
print("Total Patients", ds.count_patients())


@app.get("/")
def root():
    return {"name": "garvis-backend", "status": "ok"}
