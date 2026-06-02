from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._common import JobStatus


@dataclass
class AnimateJobResponse:
    request_id: str
    job_id: str
    status: str
    estimated_credits: int
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnimateJobResponse:
        return cls(
            request_id=data.get("requestId", ""),
            job_id=data["job_id"],
            status=data["status"],
            estimated_credits=data["estimated_credits"],
            created_at=data["created_at"],
        )


@dataclass
class AnimateResultResponse:
    request_id: str
    job_id: str
    status: JobStatus
    video_url: str | None
    duration_seconds: float | None
    credits_used: int | None
    created_at: str
    completed_at: str | None
    error: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnimateResultResponse:
        return cls(
            request_id=data.get("requestId", ""),
            job_id=data["job_id"],
            status=data["status"],
            video_url=data.get("video_url"),
            duration_seconds=data.get("duration_seconds"),
            credits_used=data.get("credits_used"),
            created_at=data["created_at"],
            completed_at=data.get("completed_at"),
            error=data.get("error"),
        )
