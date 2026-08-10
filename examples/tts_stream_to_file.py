"""Stream TTS to a WAV file.

    VOICEMAKER_API_KEY=vmk_... python examples/tts_stream_to_file.py [voice_id]

Audio chunks arrive while later sentences are still synthesizing; the WAV file
grows as they land. See the TtsStreamConnection docstring for live speaker
playback via sounddevice.
"""

from __future__ import annotations

import os
import sys

from myvoicemaker import TtsChunkEnd, TtsStreamError, VoiceMaker

API_KEY = os.environ.get("VOICEMAKER_API_KEY")
if not API_KEY:
    raise SystemExit("Set VOICEMAKER_API_KEY")

VOICE_ID = sys.argv[1] if len(sys.argv) > 1 else "amaka"
TEXT = (
    "Barka da zuwa. Wannan gwaji ne na karatun rubutu kai tsaye. "
    "Kowace jimla tana iso da zarar an gama hada ta, ba sai an jira komai ba."
)


def main() -> None:
    client = VoiceMaker(api_key=API_KEY)
    with client.tts.stream(voice_id=VOICE_ID, language="auto") as conn:
        conn.on(
            "chunk_end",
            lambda e: isinstance(e, TtsChunkEnd)
            and print(f"chunk {e.index}: {e.duration_seconds}s, {e.credits} credit(s)"),
        )
        conn.on(
            "error",
            lambda e: isinstance(e, TtsStreamError)
            and print(f"stream error [{e.code}]: {e.message}"),
        )

        conn.send_text(TEXT)
        end = conn.stream_to_file("tts_stream_output.wav")  # closes for us

    if end:
        print(
            f"done: {end.chunks} chunk(s), {end.duration_seconds}s audio, "
            f"{end.credits_used} credit(s) -> tts_stream_output.wav"
        )
    else:
        print("session ended without a summary")


if __name__ == "__main__":
    main()
