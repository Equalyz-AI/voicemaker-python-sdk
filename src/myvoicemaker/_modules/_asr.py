from __future__ import annotations

from ._base import BaseModule
from .._types._asr import TranscriptionJob
from .._types._common import PaginatedResponse
from .._utils import poll as _poll

_TERMINAL = {"completed", "failed"}


class ASRModule(BaseModule):
    def transcribe(
        self,
        audio: str,
        *,
        language: str = "auto",
        webhook_url: str | None = None,
    ) -> TranscriptionJob:
        body: dict[str, object] = {"audio": audio, "language": language}
        if webhook_url is not None:
            body["webhookUrl"] = webhook_url
        resp = self._http.post("/dev/v1/transcribe", body)
        return TranscriptionJob.from_dict(resp.data)

    def transcribe_file(
        self,
        file_path: str,
        *,
        language: str = "auto",
        webhook_url: str | None = None,
    ) -> TranscriptionJob:
        fields: dict[str, str | None] = {
            "language": language,
            "webhook_url": webhook_url,
        }
        resp = self._http.post_multipart("/dev/v1/transcribe", file_path, fields)
        return TranscriptionJob.from_dict(resp.data)

    def get_result(self, job_id: str) -> TranscriptionJob:
        resp = self._http.get(f"/dev/v1/transcribe/{job_id}")
        return TranscriptionJob.from_dict(resp.data)

    def list(
        self,
        *,
        limit: int = 20,
        cursor: str | None = None,
        status: str | None = None,
    ) -> PaginatedResponse[TranscriptionJob]:
        params: dict[str, object] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        if status is not None:
            params["status"] = status
        resp = self._http.get("/dev/v1/transcriptions", params)
        data = resp.data
        return PaginatedResponse(
            request_id=data.get("requestId", ""),
            items=[TranscriptionJob.from_dict(item) for item in data["items"]],
            next_cursor=data.get("nextCursor"),
        )

    def poll(
        self,
        job_id: str,
        *,
        interval_seconds: float = 2.0,
        timeout_seconds: float = 120.0,
    ) -> TranscriptionJob:
        return _poll(
            job_id,
            fn=lambda: self.get_result(job_id),
            is_done=lambda r: r.status in _TERMINAL,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
        )
