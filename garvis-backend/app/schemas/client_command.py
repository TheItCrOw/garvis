from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Union

class ClientCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    view: str = Field(..., description="Client screen/view identifier (e.g., 'patient', 'doctor', 'calendar', 'chat','none').")
    action: str = Field(..., description="Client action identifier (e.g., 'VIEW', 'LIST', 'none').")
    parameters: Dict[str, Union[str|int]]| None
    intent_confidence: float = Field(0.75, ge=0.0, le=1.0)
    reasoning_short: str = Field("", description="1 short sentence rationale; no private or sensitive data.")