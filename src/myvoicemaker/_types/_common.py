from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

SupportedLanguage = Literal["yo", "ig", "ha", "pcm", "en", "auto"]
JobStatus = Literal["queued", "processing", "completed", "failed"]
OutputAudioFormat = Literal["mp3", "wav", "ogg"]
OutputVideoFormat = Literal["mp4", "webm"]
AccountTier = Literal["free", "starter", "growth", "pro", "enterprise"]
UsageModule = Literal["tts", "asr", "animate", "explain"]

T = TypeVar("T")


@dataclass
class PaginatedResponse(Generic[T]):
    request_id: str
    items: list[T]
    next_cursor: str | None
