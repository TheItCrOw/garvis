from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Union

class ClientCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    view: str = Field(..., description="Client screen/view identifier (e.g., 'patient', 'doctor', 'calendar', 'chat','none').")
    action: str = Field(..., description="Client action identifier (e.g., 'VIEW', 'LIST', 'none').")
    parameters: Dict[str, Union[str|int]]| None = Field(default_factory=dict)
    intent_confidence: float = Field(0.75, ge=0.0, le=1.0)
    reasoning_short: str = Field("", description="1 short sentence rationale; no private or sensitive data.")

#I admit i didnt write this, but im already pulling my hair on how to make structuredoutput work with Gemini
CLIENT_COMMAND_RAW_SCHEMA= {
   "title": "LangGraphStructuredOutput",
   "type": "object",
   "additionalProperties": False,
   "required": ["view", "action", "intent_confidence", "reasoning_short"],
   "properties": {
       "view": {
           "type": "string",
           "enum": ["Patient", "PatientHistory", "Doctor", "Calendar", "Xray", "Medicine", "None"],
       },
       "action": {
           "type": "string",
           "enum": ["Add", "View", "Update", "Delete", "List", "None"],
       },
       "intent_confidence": {
           "type": "number",
           "format": "float",
           "minimum": 0,
           "maximum": 1,
       },
       "reasoning_short": {
           "type": "string",
           "description": "Short explanation for view/action/parameters choice. Max 512 characters.",
           "maxLength": 512
       },
       "parameters": {
           "description": "Optional parameters. Must match one of the allowed shapes. Extra keys allowed within parameters.",
           "anyOf": [
               {"$ref": "#/$defs/PatientParams"},
               {"$ref": "#/$defs/DoctorParams"},
               {"$ref": "#/$defs/DoctorDateParams"},
               {"$ref": "#/$defs/ChatModeParams"},
           ],
       },
   },
   "$defs": {
       "PatientParams": {
           "type": "object",
           "additionalProperties": True,
           "required": ["patient_id"],
           "properties": {
               "patient_id": {"type": "integer", "minimum": 1},
           },
       },
       "DoctorParams": {
           "type": "object",
           "additionalProperties": True,
           "required": ["doctor_id"],
           "properties": {
               "doctor_id": {"type": "integer", "minimum": 1},
           },
       },
       "DoctorDateParams": {
           "type": "object",
           "additionalProperties": True,
           "required": ["doctor_id", "date"],
           "properties": {
               "doctor_id": {"type": "integer", "minimum": 1},
               "date": {
                   "type": "string",
                   "description": "Use ISO-8601 full-date (YYYY-MM-DD). Example: 2026-01-01",
                   "pattern": r"^\d{4}-\d{2}-\d{2}$",
               },
           },
       },
       "ChatModeParams": {
           "type": "object",
           "additionalProperties": True,
           "required": ["mode"],
           "properties": {
               "mode": {"type": "string", "enum": ["chat"]},
           },
       },
   },
}    