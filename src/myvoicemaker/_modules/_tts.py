from __future__ import annotations

from ._base import BaseModule
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
