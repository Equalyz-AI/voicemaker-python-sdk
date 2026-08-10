from __future__ import annotations

from ._base import BaseModule
from ._tts_streaming import TtsStreamConnection
from .._types._tts import TtsGenerateResponse, VoiceListResponse


class TTSModule(BaseModule):
    def list_voices(self, *, language: str | None = None) -> VoiceListResponse:
        params = {"language": language} if language is not None else None
        resp = self._http.get("/dev/v1/tts/voices", params)
        return VoiceListResponse.from_dict(resp.data)

    def generate(
        self,
        text: str,
        voice_id: str,
        language: str,
        *,
        speed: float | None = None,
        output_format: str | None = None,
    ) -> TtsGenerateResponse:
        """Synthesize ``text`` and return a URL to the generated audio.

        ``voice_id`` is a preset id (see :meth:`list_voices`) or the id of one
        of your own custom cloned voices. ``output_format`` is ``"wav"``
        (default), ``"mp3"`` or ``"ogg"``.
        """
        body: dict[str, object] = {
            "text": text,
            "voice_id": voice_id,
            "language": language,
        }
        if speed is not None:
            body["speed"] = speed
        if output_format is not None:
            body["output_format"] = output_format

        resp = self._http.post("/dev/v1/tts/generate", body)
        return TtsGenerateResponse.from_dict(resp.data)

    def stream(
        self,
        *,
        voice_id: str,
        language: str = "auto",
        speed: float = 1.0,
        quality: str = "standard",
        access_token: "str | None" = None,
    ) -> TtsStreamConnection:
        """Open a real-time streaming synthesis session (wss /dev/v1/tts/stream).

        Audio starts arriving while later text is still generating. ``voice_id``
        is a preset id (see :meth:`list_voices`) or one of your custom voice
        ids; ``language`` is ``"auto"`` (multilingual) or ``"ha"`` (Hausa);
        ``quality`` is ``"standard"`` (lower latency) or ``"high"``.

        ``access_token`` — an ephemeral token minted by a backend holding the
        real key (``auth.create_stream_token(type="tts")``); lets untrusted
        clients stream without an ``api_key``.
        """
        url = self._http.ws_url(
            "/dev/v1/tts/stream",
            {
                "voice_id": voice_id,
                "language": language,
                "speed": speed,
                "quality": quality,
            },
        )
        return TtsStreamConnection(
            url=url,
            api_key=self._http.api_key,
            access_token=access_token,
        )
