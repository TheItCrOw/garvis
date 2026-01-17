from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(title="Garvis Backend", version="0.1.0")
app.include_router(health_router, prefix="/api")

@app.get("/")
def root():
    return {"name": "garvis-backend", "status": "ok"}