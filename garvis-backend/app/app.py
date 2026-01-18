from fastapi import FastAPI
from app.api.health import router as health_router
from app.database.data_service import DataService

app = FastAPI(title="Garvis Backend", version="0.1.0")
app.include_router(health_router, prefix="/api")

ds = DataService.initialize()
print("Total Patients", ds.count_patients())

######################################################################################
# PLAY GROUND

@app.get("/hello-world")
def hello_word():
    return {"message": "Hello World from Team Bierbingka!"}




# @app.get("/posts")
# def get_all_posts():



#######################################################################################



@app.get("/")
def root():
    return {"name": "garvis-backend", "status": "ok"}