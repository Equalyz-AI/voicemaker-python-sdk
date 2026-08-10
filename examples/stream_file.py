"""Stream a WAV file to the real-time transcription API at real-time pace.

Usage:
    VOICEMAKER_API_KEY=vmk_live_... python examples/stream_file.py audio.wav yo

The WAV must be PCM16 (stereo is downmixed); its sample rate is sent to the
API, which resamples server-side.
"""

import os
import sys
import threading
import time
import wave

from myvoicemaker import StreamSessionEnd, StreamTranscript, VoiceMaker


def read_wav(path: str) -> tuple[bytes, int]:
    with wave.open(path, "rb") as f:
        channels = f.getnchannels()
        width = f.getsampwidth()
        rate = f.getframerate()
        frames = f.readframes(f.getnframes())
    if width != 2:
        raise SystemExit("This example needs a PCM16 WAV file")
    if channels == 2:
        import audioop  # stdlib on Python <= 3.12

        frames = audioop.tomono(frames, 2, 0.5, 0.5)
    elif channels != 1:
        raise SystemExit(f"Unsupported channel count: {channels}")
    return frames, rate


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: stream_file.py <path-to-wav> [language]")
    wav_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "en"
    api_key = os.environ.get("VOICEMAKER_API_KEY")
    if not api_key:
        raise SystemExit("Set VOICEMAKER_API_KEY")

    pcm, sample_rate = read_wav(wav_path)
    print(f"Streaming {len(pcm) / (2 * sample_rate):.1f}s of {sample_rate}Hz audio ({language})...")

    client = VoiceMaker(
        api_key=api_key,
        base_url=os.environ.get("VOICEMAKER_BASE_URL", "https://api.myvoicemaker.ai"),
    )

    with client.asr.stream(language=language, sample_rate=sample_rate) as conn:

        def send_audio() -> None:
            chunk_bytes = int(sample_rate * 0.1) * 2  # 100ms per chunk
            for offset in range(0, len(pcm), chunk_bytes):
                conn.send_audio(pcm[offset : offset + chunk_bytes])
                time.sleep(0.1)
            conn.close()

        sender = threading.Thread(target=send_audio, daemon=True)
        sender.start()

        finals: list[str] = []
        for event in conn:
            if isinstance(event, StreamTranscript):
                marker = "FINAL  " if event.is_final else "interim"
                print(f"{marker} {event.text}")
                if event.is_final:
                    finals.append(event.text)
            elif isinstance(event, StreamSessionEnd):
                print(
                    f"session ended ({event.reason}) — "
                    f"{event.duration_seconds}s, {event.credits_used} credits"
                )

    print("\n--- final transcript ---")
    print(" ".join(finals))


if __name__ == "__main__":
    main()
