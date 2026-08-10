from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Voice:
    id: str
    name: str
    gender: str
    language: str
    style: str
    sample_url: str
    #: ``"preset"`` for catalog voices, ``"custom"`` for your own cloned
    #: voices (created with Clone For Me in the web app).
    type: str = "preset"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Voice:
        return cls(
            id=data["id"],
            name=data["name"],
            gender=data["gender"],
            language=data["language"],
            style=data["style"],
            sample_url=data["sample_url"],
            type=data.get("type", "preset"),
        )


@dataclass
class VoiceListResponse:
    voices: list[Voice]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoiceListResponse:
        return cls(voices=[Voice.from_dict(v) for v in data["voices"]])


@dataclass
class TtsGenerateResponse:
    request_id: str
    id: str
    audio_url: str
    duration_seconds: float | None
    characters: int
    credits_used: int
    language: str
    voice_id: str
    created_at: str
    #: Delivered audio format: ``"wav"`` (default), ``"mp3"`` or ``"ogg"``.
    output_format: str = "wav"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TtsGenerateResponse:
        return cls(
            request_id=data.get("requestId", ""),
            id=data["id"],
            audio_url=data["audio_url"],
            duration_seconds=data.get("duration_seconds"),
            characters=data["characters"],
            credits_used=data["credits_used"],
            language=data["language"],
            voice_id=data["voice_id"],
            created_at=data["created_at"],
            output_format=data.get("output_format", "wav"),
        )
