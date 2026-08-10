from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class StreamSessionBegin:
    session_id: str
    request_id: str
    language: str
    sample_rate: int
    encoding: str
    interim_results: bool
    max_duration_seconds: int
    credits_per_second: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StreamSessionBegin":
        return cls(
            session_id=str(data.get("session_id", "")),
            request_id=str(data.get("request_id", "")),
            language=str(data.get("language", "")),
            sample_rate=int(data.get("sample_rate", 16000)),
            encoding=str(data.get("encoding", "linear16")),
            interim_results=bool(data.get("interim_results", True)),
            max_duration_seconds=int(data.get("max_duration_seconds", 0)),
            credits_per_second=int(data.get("credits_per_second", 0)),
        )


@dataclass(frozen=True)
class StreamTranscript:
    text: str
    is_final: bool
    start: Optional[float]
    end: Optional[float]
    confidence: Optional[float]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StreamTranscript":
        start = data.get("start")
        end = data.get("end")
        confidence = data.get("confidence")
        return cls(
            text=str(data.get("text", "")),
            is_final=bool(data.get("is_final", False)),
            start=float(start) if isinstance(start, (int, float)) else None,
            end=float(end) if isinstance(end, (int, float)) else None,
            confidence=(
                float(confidence) if isinstance(confidence, (int, float)) else None
            ),
        )


@dataclass(frozen=True)
class StreamSessionEnd:
    session_id: str
    duration_seconds: int
    credits_used: int
    reason: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StreamSessionEnd":
        return cls(
            session_id=str(data.get("session_id", "")),
            duration_seconds=int(data.get("duration_seconds", 0)),
            credits_used=int(data.get("credits_used", 0)),
            reason=str(data.get("reason", "")),
        )


@dataclass(frozen=True)
class StreamError:
    code: str
    message: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StreamError":
        return cls(
            code=str(data.get("code", "internal_error")),
            message=str(data.get("message", "")),
        )
