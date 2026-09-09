from __future__ import annotations

from ._base import BaseModule
from ._streaming import AsrStreamConnection
from .._errors import InvalidArgumentError
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
        resp = self._http.post("/dev/v1/transcribe", body, method="asr.transcribe")
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
        resp = self._http.post_multipart(
            "/dev/v1/transcribe", file_path, fields, method="asr.transcribe_file"
        )
        return TranscriptionJob.from_dict(resp.data)

    def get_result(self, job_id: str) -> TranscriptionJob:
        resp = self._http.get(f"/dev/v1/transcribe/{job_id}", None, method="asr.get_result")
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
        resp = self._http.get("/dev/v1/transcriptions", params, method="asr.list")
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
            method="asr.poll",
        )

    def stream(
        self,
        *,
        language: str,
        sample_rate: int = 16000,
        interim_results: bool = True,
        access_token: "str | None" = None,
    ) -> AsrStreamConnection:
        """Open a real-time streaming transcription session (WebSocket).

        ``language`` must be explicit (``yo``, ``ig``, ``ha``, ``pcm`` or
        ``en`` — auto-detection is batch-only). Send PCM16LE mono audio at
        ``sample_rate`` with ``send_audio()``; iterate the connection for
        interim and final transcripts.

        ``access_token`` — an ephemeral token minted by a backend holding the
        real key (``auth.create_stream_token(type="asr")``); lets untrusted
        clients stream without an ``api_key``.
        """
        if not language or language == "auto":
            raise InvalidArgumentError(
                "language",
                "streaming needs an explicit language code (auto-detection is "
                "batch-only); pick one from tts.list_languages() such as "
                '"en", "yo", "ha", "ig" or "pcm".',
                "asr.stream",
            )
        url = self._http.ws_url(
            "/dev/v1/transcribe/stream",
            {
                "language": language,
                "sample_rate": sample_rate,
                "interim_results": "true" if interim_results else "false",
            },
        )
        return AsrStreamConnection(
            url=url,
            api_key=self._http.api_key,
            access_token=access_token,
            method="asr.stream",
        )
