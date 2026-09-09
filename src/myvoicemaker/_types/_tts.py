from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._common import JobStatus


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
class TtsLanguage:
    #: Pass this as ``language`` in :meth:`generate` / :meth:`stream`.
    code: str
    label: str
    #: Whether voice selection/cloning is currently available for this language.
    supports_voice_clone: bool
    supports_tone: bool
    supports_speed: bool
    #: Whether the streaming endpoint accepts this language.
    streaming_supported: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TtsLanguage:
        return cls(
            code=data["code"],
            label=data["label"],
            supports_voice_clone=data.get("supports_voice_clone", False),
            supports_tone=data.get("supports_tone", False),
            supports_speed=data.get("supports_speed", False),
            streaming_supported=data.get("streaming_supported", False),
        )


@dataclass
class TtsLanguageListResponse:
    #: Code that requests without a ``language`` resolve to.
    default_language: str
    languages: list[TtsLanguage]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TtsLanguageListResponse:
        return cls(
            default_language=data.get("default_language", ""),
            languages=[TtsLanguage.from_dict(l) for l in data["languages"]],
        )


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


@dataclass
class TtsJobResponse:
    """Result of ``tts.generate(..., mode="async")``: the queued job."""

    request_id: str
    id: str
    status: str
    characters: int
    #: Credits reserved for the job; settled to the real cost on completion.
    credits_reserved: int
    language: str
    voice_id: str
    created_at: str
    output_format: str = "wav"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TtsJobResponse:
        return cls(
            request_id=data.get("requestId", ""),
            id=data["id"],
            status=data.get("status", "queued"),
            characters=data.get("characters", 0),
            credits_reserved=data.get("credits_reserved", 0),
            language=data.get("language", ""),
            voice_id=data.get("voice_id", ""),
            created_at=data.get("created_at", ""),
            output_format=data.get("output_format", "wav"),
        )


@dataclass
class TtsResultResponse:
    """Result of ``tts.get_result()`` / ``tts.poll()``. ``audio_url`` is set once
    ``status`` is ``"completed"``; ``error`` once it is ``"failed"``."""

    request_id: str
    id: str
    status: JobStatus
    audio_url: str | None
    duration_seconds: float | None
    characters: int | None
    credits_used: int | None
    language: str
    voice_id: str
    error: str | None
    created_at: str
    completed_at: str | None
    output_format: str = "wav"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TtsResultResponse:
        return cls(
            request_id=data.get("requestId", ""),
            id=data["id"],
            status=data["status"],
            audio_url=data.get("audio_url"),
            duration_seconds=data.get("duration_seconds"),
            characters=data.get("characters"),
            credits_used=data.get("credits_used"),
            language=data.get("language", ""),
            voice_id=data.get("voice_id", ""),
            error=data.get("error"),
            created_at=data.get("created_at", ""),
            completed_at=data.get("completed_at"),
            output_format=data.get("output_format", "wav"),
        )
