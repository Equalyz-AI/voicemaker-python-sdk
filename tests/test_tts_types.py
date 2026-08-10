"""Offline tests for TTS response type parsing (no network needed)."""

from __future__ import annotations

from myvoicemaker._types._tts import TtsGenerateResponse, Voice, VoiceListResponse

PRESET_PAYLOAD = {
    "id": "amaka",
    "name": "Amaka",
    "gender": "female",
    "language": "auto",
    "style": "conversational",
    "sample_url": "https://cdn.example/amaka.wav",
}


class TestVoice:
    def test_defaults_to_preset_when_type_missing(self) -> None:
        # Older servers omit "type"; parsing must not break.
        voice = Voice.from_dict(PRESET_PAYLOAD)
        assert voice.type == "preset"

    def test_parses_custom_voice_type(self) -> None:
        voice = Voice.from_dict({**PRESET_PAYLOAD, "type": "custom"})
        assert voice.type == "custom"

    def test_list_response_mixes_presets_and_custom(self) -> None:
        resp = VoiceListResponse.from_dict(
            {
                "voices": [
                    {**PRESET_PAYLOAD, "type": "preset"},
                    {
                        "id": "cmcustom123",
                        "name": "My Clone",
                        "gender": "male",
                        "language": "English",
                        "style": "Personal",
                        "sample_url": "https://cdn.example/clone.wav",
                        "type": "custom",
                    },
                ]
            }
        )
        assert [v.type for v in resp.voices] == ["preset", "custom"]


class TestTtsGenerateResponse:
    BASE = {
        "requestId": "req-1",
        "id": "vit_123",
        "audio_url": "https://cdn.example/out.mp3",
        "duration_seconds": 3.2,
        "characters": 31,
        "credits_used": 31,
        "language": "yo",
        "voice_id": "amaka",
        "created_at": "2026-08-10T10:30:00Z",
    }

    def test_defaults_to_wav_when_output_format_missing(self) -> None:
        resp = TtsGenerateResponse.from_dict(self.BASE)
        assert resp.output_format == "wav"

    def test_parses_output_format(self) -> None:
        resp = TtsGenerateResponse.from_dict({**self.BASE, "output_format": "mp3"})
        assert resp.output_format == "mp3"
