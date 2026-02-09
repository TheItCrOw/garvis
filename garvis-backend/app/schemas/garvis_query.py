from fastapi import FastAPI, File, UploadFile, Form, Depends
from pydantic import BaseModel

# 1. Define your data model
class GarvisQuery(BaseModel):
    session_id: str
    query: str

    @classmethod
    def as_form(
        cls,
        session_id: str = Form(...),
        query: str = Form(...),
    ) -> "GarvisQuery":
        return cls(session_id=session_id, query=query)    