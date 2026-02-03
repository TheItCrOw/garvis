from dataclasses import dataclass
import json


@dataclass
class GarvisTask:
    session_id: str
    query: str


@dataclass
class GarvisReply:
    session_id: str
    query: str
    reply: str
    view: str = ""
    action: str = ""
    parameters: json = None
