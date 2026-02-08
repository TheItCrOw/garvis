import os
import shutil
import tempfile

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.calendar import router as calendar_router
from app.api.patient import router as patients_router
from app.api.xray import router as xrays_router
from app.database.duckdb_data_service import DataService
from app.core.dto.garvis_dtos import GarvisTask
from app.core.garvis import get_garvis
from app.api.ws_garvis_router import router as ws_garvis_router
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Garvis Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_garvis_router)
app.include_router(health_router, prefix="/api")
app.include_router(calendar_router, prefix="/api")
app.include_router(patients_router, prefix="/api")
app.include_router(xrays_router, prefix="/api")
print(f"LLM Flavor: {os.getenv("LLM_FLAVOR")}")
garvis = get_garvis()


@app.get("/")
def root():
    return {"name": "garvis-backend", "status": "ok"}

# 1. Define your data model
class Item(BaseModel):
    session_id: str
    query: str

@app.post("/invoke_agent/")
async def invoke_agent(item: Item):
    task = GarvisTask(session_id=item.session_id, query=item.query)
    reply = await garvis.handle_task(task)
    return {
        "message": "Item created successfully",
        "item_name": item.session_id,
        "agent_message": reply.reply,
        "view": reply.view,
        "action": reply.action,
        "parameters": reply.parameters,
        "intent_confidence": reply.intent_confidence,
    }

@app.post("/invoke_agent_with_file/")
async def invoke_agent_with_file(
    uploaded_file: UploadFile = File(...),
    session_id: str = Form(...),
    query: str = Form(...),
):

    temp_file_path = None

    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(uploaded_file.filename)[1]
    ) as temp_file:
        uploaded_file.file.seek(0)  # safe even if already at 0
        shutil.copyfileobj(uploaded_file.file, temp_file)
        temp_file_path = temp_file.name

    task = GarvisTask(session_id=session_id
                      , query=query
                      , uploaded_file_path=temp_file_path)
    
    reply = await garvis.handle_task(task)

    return {
        "message": "Item created successfully",
        "item_name": session_id,
        "agent_message": reply.reply,
        "view": reply.view,
        "action": reply.action,
        "parameters": reply.parameters,
        "intent_confidence": reply.intent_confidence,
    }