from dataclasses import dataclass

@dataclass
class GarvisTask:
    session_id: str
    query: str