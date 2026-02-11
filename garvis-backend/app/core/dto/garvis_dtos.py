from dataclasses import dataclass
import json


@dataclass
class GarvisReply:
    session_id: str
    query: str
    reply: str
    view: str = ""
    action: str = ""
    parameters: json = None
    intent_confidence: float = None


@dataclass
class GarvisTask:
    session_id: str
    query: str
    uploaded_file_path:str= None
    base64_image:str=None
