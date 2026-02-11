from fastapi import Form
from pydantic import BaseModel
from typing import Optional

class GarvisQuery(BaseModel):
    session_id: str
    query: str
    base64_image: Optional[str] = ""  

    @classmethod
    def as_form(
        cls,
        session_id: str = Form(...),
        query: str = Form(...),
        base64_image: Optional[str] = Form(None, description="Base64 image", example="")
    ) -> "GarvisQuery":
        return cls(session_id=session_id, query=query, base64_image=base64_image)