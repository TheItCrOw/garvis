from fastapi import FastAPI
from app.api.health import router as health_router
from app.database.duckdb_database import DataService

app = FastAPI(title="Garvis Backend", version="0.1.0")
app.include_router(health_router, prefix="/api")

ds = DataService()
print("Total Patients", ds.count_patients())

@app.get("/hello-world")
def hello_word():
    return {"message": "Hello World from Team Bierbingka!"}

@app.get("/")
def root():
    return {"name": "garvis-backend", "status": "ok"}