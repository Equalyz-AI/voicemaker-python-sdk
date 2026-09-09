from __future__ import annotations

from typing import Literal, Union, overload

from ._base import BaseModule
from ._tts_streaming import TtsStreamConnection
from .._types._tts import (
    TtsGenerateResponse,
    TtsJobResponse,
    TtsLanguageListResponse,
    TtsResultResponse,
    VoiceListResponse,
)
from .._utils import poll as _poll

_TERMINAL = {"completed", "failed"}


class TTSModule(BaseModule):
    def list_languages(self) -> TtsLanguageListResponse:
        """List the languages the platform currently supports for synthesis.

        The set is configured by platform admins and can change at runtime —
        prefer this over hardcoding language codes.
        """
        resp = self._http.get("/dev/v1/tts/languages", None, method="tts.list_languages")
        return TtsLanguageListResponse.from_dict(resp.data)

    def list_voices(self, *, language: str | None = None) -> VoiceListResponse:
        params = {"language": language} if language is not None else None
        resp = self._http.get("/dev/v1/tts/voices", params, method="tts.list_voices")
        return VoiceListResponse.from_dict(resp.data)

    @overload
    def generate(
        self,
        text: str,
        voice_id: str,
        language: str | None = None,
        *,
        speed: float | None = None,
        output_format: str | None = None,
        mode: Literal["async"],
    ) -> TtsJobResponse: ...

    @overload
    def generate(
        self,
        text: str,
        voice_id: str,
        language: str | None = None,
        *,
        speed: float | None = None,
        output_format: str | None = None,
        mode: Literal["sync"] = "sync",
    ) -> TtsGenerateResponse: ...

    def generate(
        self,
        text: str,
        voice_id: str,
        language: str | None = None,
        *,
        speed: float | None = None,
        output_format: str | None = None,
        mode: str = "sync",
    ) -> Union[TtsGenerateResponse, TtsJobResponse]:
        """Synthesize ``text``.

        Default (``mode="sync"``) returns a URL to the generated audio. Pass
        ``mode="async"`` to queue the job instead — it never hits the
        concurrency cap and survives engine cold starts; poll it with
        :meth:`get_result` or :meth:`poll`.

        ``voice_id`` is a preset id (see :meth:`list_voices`) or the id of one
        of your own custom cloned voices. ``language`` is a code from
        :meth:`list_languages`; omitted, the platform's default language is
        used. ``output_format`` is ``"wav"`` (default), ``"mp3"`` or ``"ogg"``.
        """
        body: dict[str, object] = {
            "text": text,
            "voice_id": voice_id,
        }
        if language is not None:
            body["language"] = language
        if speed is not None:
            body["speed"] = speed
        if output_format is not None:
            body["output_format"] = output_format
        if mode != "sync":
            body["mode"] = mode

        resp = self._http.post("/dev/v1/tts/generate", body, method="tts.generate")
        if mode == "async" or "audio_url" not in resp.data:
            return TtsJobResponse.from_dict(resp.data)
        return TtsGenerateResponse.from_dict(resp.data)

    def get_result(self, id: str) -> TtsResultResponse:
        """Fetch the state of a job created with ``generate(..., mode="async")``."""
        resp = self._http.get(f"/dev/v1/tts/{id}", None, method="tts.get_result")
        return TtsResultResponse.from_dict(resp.data)

    def poll(
        self,
        id: str,
        *,
        interval_seconds: float = 2.0,
        timeout_seconds: float = 120.0,
    ) -> TtsResultResponse:
        """Poll an async TTS job until it completes or fails."""
        return _poll(
            id,
            fn=lambda: self.get_result(id),
            is_done=lambda r: r.status in _TERMINAL,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            method="tts.poll",
        )

    def stream(
        self,
        *,
        voice_id: str,
        language: str | None = None,
        speed: float = 1.0,
        quality: str = "standard",
        access_token: "str | None" = None,
    ) -> TtsStreamConnection:
        """Open a real-time streaming synthesis session (wss /dev/v1/tts/stream).

        Audio starts arriving while later text is still generating. ``voice_id``
        is a preset id (see :meth:`list_voices`) or one of your custom voice
        ids; ``language`` is a code from :meth:`list_languages` (only languages
        with ``streaming_supported`` are accepted) — omitted, the platform's
        default language is used; ``quality`` is ``"standard"`` (lower latency)
        or ``"high"``.

        ``access_token`` — an ephemeral token minted by a backend holding the
        real key (``auth.create_stream_token(type="tts")``); lets untrusted
        clients stream without an ``api_key``.
        """
        query: dict[str, object] = {
            "voice_id": voice_id,
            "speed": speed,
            "quality": quality,
        }
        # Omitted → the server resolves the platform's default language.
        if language is not None:
            query["language"] = language
        url = self._http.ws_url("/dev/v1/tts/stream", query)
        return TtsStreamConnection(
            url=url,
            api_key=self._http.api_key,
            access_token=access_token,
            method="tts.stream",
        )
