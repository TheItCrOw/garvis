from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.calendar import router as calendar_router
from app.database.duckdb_data_service import DataService
from contextlib import asynccontextmanager
from pydantic import BaseModel
from app.core.garvis import Garvis
from app.core.garvis_task import GarvisTask
from app.services.agentic_assistant_service import AgenticAssistantService

from app.api.ws_garvis_router import router as ws_garvis_router

load_dotenv()
current_agent = AgenticAssistantService()

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
ds = DataService()
print("Total Patients", ds.count_patients())


@app.get("/")
def root():
    return {"name": "garvis-backend", "status": "ok"}


# 1. Define your data model
class Item(BaseModel):
    session_id: str
    query: str


@app.post("/invoke_agent/")
async def invoke_agent(item: Item):
    garvis = Garvis(current_agent)
    task = GarvisTask(session_id=item.session_id, query=item.query)
    reply = await garvis.handle_task(task)
    return {
        "message": "Item created successfully",
        "item_name": item.session_id,
        "agent_message": reply,
    }
