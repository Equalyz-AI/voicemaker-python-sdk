from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class TtsSessionBegin:
    session_id: str
    request_id: str
    language: str
    voice_id: str
    sample_rate: int
    encoding: str
    quality: str
    speed: float
    credits_per_character: int
    max_session_characters: int
    max_duration_seconds: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TtsSessionBegin":
        return cls(
            session_id=str(data.get("session_id", "")),
            request_id=str(data.get("request_id", "")),
            language=str(data.get("language", "")),
            voice_id=str(data.get("voice_id", "")),
            sample_rate=int(data.get("sample_rate", 24000)),
            encoding=str(data.get("encoding", "pcm_s16le")),
            quality=str(data.get("quality", "standard")),
            speed=float(data.get("speed", 1.0)),
            credits_per_character=int(data.get("credits_per_character", 0)),
            max_session_characters=int(data.get("max_session_characters", 0)),
            max_duration_seconds=int(data.get("max_duration_seconds", 0)),
        )


@dataclass(frozen=True)
class TtsChunkStart:
    index: int
    submission_id: Optional[str]
    text: str
    characters: int
    credits: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TtsChunkStart":
        submission_id = data.get("submission_id")
        return cls(
            index=int(data.get("index", 0)),
            submission_id=str(submission_id) if submission_id is not None else None,
            text=str(data.get("text", "")),
            characters=int(data.get("characters", 0)),
            credits=int(data.get("credits", 0)),
        )


@dataclass(frozen=True)
class TtsChunkEnd:
    index: int
    submission_id: Optional[str]
    characters: int
    credits: int
    duration_seconds: float
    audio_bytes: Optional[int]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TtsChunkEnd":
        submission_id = data.get("submission_id")
        audio_bytes = data.get("audio_bytes")
        return cls(
            index=int(data.get("index", 0)),
            submission_id=str(submission_id) if submission_id is not None else None,
            characters=int(data.get("characters", 0)),
            credits=int(data.get("credits", 0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            audio_bytes=int(audio_bytes) if isinstance(audio_bytes, (int, float)) else None,
        )


@dataclass(frozen=True)
class TtsAudioChunk:
    """One binary PCM16LE frame, tagged with the chunk it belongs to."""

    index: int
    data: bytes


@dataclass(frozen=True)
class TtsFinalized:
    """Ack for finalize(): everything sent so far is synthesized and delivered."""


@dataclass(frozen=True)
class TtsSessionEnd:
    session_id: str
    total_characters: int
    credits_used: int
    duration_seconds: float
    chunks: int
    reason: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TtsSessionEnd":
        return cls(
            session_id=str(data.get("session_id", "")),
            total_characters=int(data.get("total_characters", 0)),
            credits_used=int(data.get("credits_used", 0)),
            duration_seconds=float(data.get("duration_seconds", 0.0)),
            chunks=int(data.get("chunks", 0)),
            reason=str(data.get("reason", "")),
        )


@dataclass(frozen=True)
class TtsStreamError:
    code: str
    message: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TtsStreamError":
        return cls(
            code=str(data.get("code", "internal_error")),
            message=str(data.get("message", "")),
        )
