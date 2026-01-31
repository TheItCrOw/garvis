from dataclasses import dataclass

@dataclass
class GarvisTask:
    session_id: str
    query: str

@dataclass
class GarvisReply:
    session_id: str
    query: str
    reply: str    