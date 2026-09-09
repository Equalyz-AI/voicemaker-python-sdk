from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

#: Language codes known at the time this SDK version was released. The live
#: set is configured by platform admins and can change at runtime — discover
#: it with ``client.tts.list_languages()``.
KnownLanguage = Literal["yo", "ig", "ha", "pcm", "en", "auto"]

#: Any language code the platform currently supports. Kept open (``str``)
#: because the catalog is server-configured.
SupportedLanguage = str
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
