from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict, Sequence, Dict, Any, Optional
from pydantic import Field
from langchain_core.messages import BaseMessage

class AgentState(TypedDict, total=False):
    messages:Annotated[Sequence[BaseMessage], add_messages]
    view: str = Field(..., description="Client screen/view identifier (e.g., 'home', 'search', 'ticket', 'chat').")
    action: str = Field(..., description="Client action identifier (e.g., 'NAVIGATE', 'SHOW_RESULTS', 'CREATE_DRAFT').")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action payload; must be JSON-serializable.")
    intent_confidence: float = Field(0.75, ge=0.0, le=1.0)
    reasoning_short: str = Field("", description="1 short sentence rationale; no private or sensitive data.")
    image_b64: Optional[str]
    image_mime: Optional[str]