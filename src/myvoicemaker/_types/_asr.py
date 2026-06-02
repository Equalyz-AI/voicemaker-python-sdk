from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._common import JobStatus


@dataclass
class TranscriptionJob:
    request_id: str
    job_id: str
    status: JobStatus
    language: str
    detected_language: str | None
    text: str | None
    confidence: float | None
    duration_seconds: float | None
    credits_used: int | None
    created_at: str
    completed_at: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranscriptionJob:
        return cls(
            request_id=data.get("requestId", ""),
            job_id=data["job_id"],
            status=data["status"],
            language=data["language"],
            detected_language=data.get("detected_language"),
            text=data.get("text"),
            confidence=data.get("confidence"),
            duration_seconds=data.get("duration_seconds"),
            credits_used=data.get("credits_used"),
            created_at=data["created_at"],
            completed_at=data.get("completed_at"),
        )
