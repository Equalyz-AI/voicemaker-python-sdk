"""Offline tests for the streaming-TTS helpers (no network needed)."""

from __future__ import annotations

import wave

from myvoicemaker import chunk_text
from myvoicemaker._types._tts_stream import (
    TtsChunkEnd,
    TtsSessionBegin,
    TtsSessionEnd,
)


class TestChunkText:
    def test_merges_tiny_sentences_up_to_cap(self) -> None:
        chunks = chunk_text("Yes. No way. Maybe so. Sure thing.", max_chars=80, first_chunk_max_chars=80)
        assert chunks == ["Yes. No way. Maybe so. Sure thing."]

    def test_first_chunk_uses_smaller_cap(self) -> None:
        text = (
            "One short sentence here. Another short sentence here. "
            "A third short sentence follows right after."
        )
        chunks = chunk_text(text, max_chars=100, first_chunk_max_chars=30)
        assert len(chunks) > 1
        assert len(chunks[0]) <= 30
        assert all(len(c) <= 100 for c in chunks)

    def test_never_splits_words(self) -> None:
        word = "supercalifragilistic"
        chunks = chunk_text(" ".join([word] * 12), max_chars=25, first_chunk_max_chars=25)
        for chunk in chunks:
            assert all(piece == word for piece in chunk.split(" "))

    def test_abbreviations_do_not_end_sentences(self) -> None:
        chunks = chunk_text(
            "Mr. Musa arrived at No. 5 today. He was early.",
            max_chars=120,
            first_chunk_max_chars=120,
        )
        assert chunks == ["Mr. Musa arrived at No. 5 today. He was early."]

    def test_hausa_text_chunks_on_standard_punctuation(self) -> None:
        chunks = chunk_text(
            "Barka da zuwa gidan rediyon mu. Yau za mu tattauna labarai. Ku zauna lafiya.",
            max_chars=45,
            first_chunk_max_chars=45,
        )
        assert len(chunks) >= 2
        assert all(c.endswith(".") for c in chunks)

    def test_empty_input(self) -> None:
        assert chunk_text("   \n  ") == []


class TestTypes:
    def test_session_begin_from_dict_defaults(self) -> None:
        begin = TtsSessionBegin.from_dict({"session_id": "s", "speed": 1.2})
        assert begin.sample_rate == 24000
        assert begin.encoding == "pcm_s16le"
        assert begin.speed == 1.2

    def test_chunk_end_from_dict(self) -> None:
        end = TtsChunkEnd.from_dict(
            {"index": 3, "characters": 14, "credits": 14, "duration_seconds": 1.5, "audio_bytes": 72000}
        )
        assert end.index == 3 and end.audio_bytes == 72000

    def test_session_end_from_dict(self) -> None:
        end = TtsSessionEnd.from_dict(
            {"session_id": "s", "total_characters": 99, "credits_used": 99, "chunks": 4, "reason": "client_close"}
        )
        assert end.total_characters == 99 and end.reason == "client_close"


class TestWavWriting:
    def test_wave_module_writes_valid_pcm16_mono(self, tmp_path) -> None:
        # stream_to_file relies on the stdlib wave module patching sizes on
        # close; verify the exact write pattern it uses produces a valid file.
        path = tmp_path / "out.wav"
        with wave.open(str(path), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(24000)
            out.writeframes(b"\x00\x00" * 12000)
            out.writeframes(b"\x00\x00" * 12000)
        with wave.open(str(path), "rb") as check:
            assert check.getnchannels() == 1
            assert check.getframerate() == 24000
            assert check.getnframes() == 24000  # exactly 1 second
