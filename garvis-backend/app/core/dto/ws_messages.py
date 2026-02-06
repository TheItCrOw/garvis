from __future__ import annotations
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import json
from typing import Any, Dict, Generic, Optional, Type, TypeVar
import uuid


class WsMessageType(str, Enum):
    START_RECORDING = "startRecording"
    STOP_RECORDING = "stopRecording"
    LOGIN = "login"
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

    @classmethod
    def create(cls, type: WsMessageType, content: T) -> "WsMessage[T]":
        return cls(id=str(uuid.uuid4()), type=type, content=content)

    def to_json(self) -> Dict[str, Any]:
        content = self.content

        if hasattr(content, "to_json"):
            content = content.to_json()
        elif is_dataclass(content):
            content = asdict(content)

        return {"id": self.id, "type": self.type.value, "content": content}

    @classmethod
    def from_json(
        cls,
        data: Dict[str, Any],
        content_cls: Optional[Type[T]] = None,
    ) -> "WsMessage[T]":
        raw_content = data.get("content")
        if content_cls is not None and hasattr(content_cls, "from_json"):
            content = content_cls.from_json(raw_content)
        else:
            content = raw_content
        return cls(id=data["id"], type=WsMessageType(data["type"]), content=content)


@dataclass
class WsStartRecordingContent:
    format: str
    sampleRate: int
    channels: int
    interimResults: bool
    languageCode: str

    def to_json(self) -> Dict[str, Any]:
        return {
            "format": self.format,
            "sampleRate": self.sampleRate,
            "channels": self.channels,
            "interimResults": self.interimResults,
            "languageCode": self.languageCode,
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "WsStartRecordingContent":
        return cls(
            format=data["format"],
            sampleRate=int(data["sampleRate"]),
            channels=int(data["channels"]),
            interimResults=bool(data["interimResults"]),
            languageCode=str(data["languageCode"]),
        )


@dataclass
class WsGarvisContent:
    intent: str = ""
    user_query: str = ""
    answer: str = ""
    audio_base64: str = ""
    audio_mime_type: str = ""
    open_view: str = ""
    action: str = ""
    parameters: json = None
    intent_confidence: float = None


@dataclass
class WsStopRecordingContent:
    reason: str = ""


@dataclass
class WsLoginContent:

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "WsStartRecordingContent":
        return cls(
            doctor_id=int(data["doctor_id"]),
        )

    doctor_id: int = -1


@dataclass
class WsAckContent:
    message: str


@dataclass
class WsTranscriptContent:
    text: str
    final: bool


@dataclass
class WsErrorContent:
    message: str
