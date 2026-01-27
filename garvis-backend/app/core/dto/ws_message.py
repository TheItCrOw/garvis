from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, Optional, Type, TypeVar
import uuid


class WsMessageType(str, Enum):
    START = "start"
    STOP = "stop"
    ACK = "ack"
    TRANSCRIPT = "transcript"
    GARVIS = "garvis"
    ERROR = "error"
    END = "end"


T = TypeVar("T")


@dataclass
class WsMessage(Generic[T]):
    id: str
    type: WsMessageType
    content: T

    def __init__(self, type: WsMessageType, content: T):
        self.id = str(uuid.uuid4())
        self.type = type
        self.content = content

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "content": (
                self.content.to_json()
                if hasattr(self.content, "to_json")
                else self.content
            ),
        }

    @classmethod
    def from_json(
        cls,
        data: Dict[str, Any],
        content_cls: Optional[Type[T]] = None,
    ) -> "WsMessage[T]":
        content_raw = data.get("content")

        if content_cls and hasattr(content_cls, "from_json"):
            content = content_cls.from_json(content_raw)
        else:
            content = content_raw

        return cls(
            id=data["id"],
            type=WsMessageType(data["type"]),
            content=content,
        )
