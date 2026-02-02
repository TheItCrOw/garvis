from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict, Sequence, Literal
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

class AgentState(TypedDict, total=False):
    messages:Annotated[Sequence[BaseMessage], add_messages]
    view: Literal["none","patient","doctor"]
    action: Literal["view","list"]