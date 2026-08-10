from __future__ import annotations

import json
import queue
import threading
import wave
from typing import Callable, Iterator, Optional, Union

from .._types._tts_stream import (
    TtsAudioChunk,
    TtsChunkEnd,
    TtsChunkStart,
    TtsFinalized,
    TtsSessionBegin,
    TtsSessionEnd,
    TtsStreamError,
)

TtsStreamEvent = Union[
    TtsSessionBegin,
    TtsChunkStart,
    TtsAudioChunk,
    TtsChunkEnd,
    TtsFinalized,
    TtsSessionEnd,
    TtsStreamError,
]

_KEEPALIVE_INTERVAL_S = 10.0
# The server synthesizes all queued text before session.end — each pending
# chunk needs a full GPU pass, so this is much longer than the ASR grace.
_CLOSE_GRACE_S = 60.0


class TtsStreamConnection:
    """Streaming text-to-speech session over a WebSocket (sync API).

    Submit text with :meth:`send_text` (whole paragraphs or incremental
    sentences — the server splits into sentence-sized chunks itself); consume
    typed events by iterating the connection, via ``on(...)`` callbacks, or
    with the :meth:`audio_chunks` / :meth:`stream_to_file` helpers. Audio is
    raw PCM16LE mono at ``session.sample_rate`` (24 kHz)::

        with client.tts.stream(voice_id="amaka") as conn:
            conn.send_text("Sannu da zuwa. Yaya kake a yau?")
            conn.stream_to_file("out.wav")  # sends CloseStream by default

    Live speaker playback (requires ``pip install sounddevice numpy``,
    deliberately NOT a dependency of this SDK)::

        import numpy as np
        import sounddevice as sd

        with client.tts.stream(voice_id="amaka") as conn:
            conn.send_text(text)
            with sd.OutputStream(samplerate=24000, channels=1, dtype="int16") as out:
                for pcm in conn.audio_chunks(close=True):
                    out.write(np.frombuffer(pcm, dtype=np.int16))

    For interactive sessions (keep submitting text while audio plays), pass
    ``close=False`` to the helpers, consume events yourself, and end the
    session with :meth:`close` when you are done.

    Requires the ``websockets`` package (installed with this SDK).
    """

    def __init__(
        self,
        *,
        url: str,
        api_key: "str | None" = None,
        access_token: "str | None" = None,
        keepalive_interval: float = _KEEPALIVE_INTERVAL_S,
    ) -> None:
        try:
            from websockets.sync.client import connect
        except ImportError as exc:  # pragma: no cover - packaging guard
            raise RuntimeError(
                "Streaming requires the 'websockets' package (pip install websockets)."
            ) from exc

        # Ephemeral stream tokens (auth.create_stream_token) take precedence —
        # they travel through the same Authorization channel as the key.
        credential = access_token or api_key
        if not credential:
            raise ValueError(
                "Streaming requires an api_key or an access_token "
                "(mint one server-side via auth.create_stream_token)."
            )

        self._ws = connect(
            url,
            additional_headers={"Authorization": f"Bearer {credential}"},
            max_size=None,
        )
        self._events: "queue.Queue[Optional[TtsStreamEvent]]" = queue.Queue()
        self._callbacks: dict[str, list[Callable[[TtsStreamEvent], None]]] = {}
        self._session_begin: Optional[TtsSessionBegin] = None
        self._session_end: Optional[TtsSessionEnd] = None
        self._closed = threading.Event()
        self._keepalive_interval = max(1.0, keepalive_interval)
        self._current_chunk_index = 0

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._keepalive = threading.Thread(target=self._keepalive_loop, daemon=True)
        self._keepalive.start()

    # -- receiving -----------------------------------------------------------

    def _read_loop(self) -> None:
        try:
            while True:
                raw = self._ws.recv()
                if isinstance(raw, str):
                    event = self._parse_event(raw)
                    if event is None:
                        continue
                    self._dispatch(event)
                    continue
                if isinstance(raw, (bytes, bytearray)):
                    self._dispatch(
                        TtsAudioChunk(
                            index=self._current_chunk_index, data=bytes(raw)
                        )
                    )
        except Exception:
            pass
        finally:
            self._closed.set()
            self._events.put(None)

    def _parse_event(self, raw: str) -> Optional[TtsStreamEvent]:
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        event_type = data.get("type")
        if event_type == "session.begin":
            self._session_begin = TtsSessionBegin.from_dict(data)
            return self._session_begin
        if event_type == "chunk.start":
            event = TtsChunkStart.from_dict(data)
            self._current_chunk_index = event.index
            return event
        if event_type == "chunk.end":
            return TtsChunkEnd.from_dict(data)
        if event_type == "finalized":
            return TtsFinalized()
        if event_type == "session.end":
            self._session_end = TtsSessionEnd.from_dict(data)
            return self._session_end
        if event_type == "error":
            return TtsStreamError.from_dict(data)
        return None

    def _dispatch(self, event: TtsStreamEvent) -> None:
        name = {
            TtsSessionBegin: "open",
            TtsChunkStart: "chunk_start",
            TtsAudioChunk: "audio",
            TtsChunkEnd: "chunk_end",
            TtsFinalized: "finalized",
            TtsSessionEnd: "end",
            TtsStreamError: "error",
        }[type(event)]
        for callback in self._callbacks.get(name, []):
            try:
                callback(event)
            except Exception:
                pass
        self._events.put(event)

    def on(
        self, event: str, callback: Callable[[TtsStreamEvent], None]
    ) -> "TtsStreamConnection":
        """Register a callback for "open", "chunk_start", "audio", "chunk_end",
        "finalized", "end" or "error". Callbacks run on the reader thread."""
        self._callbacks.setdefault(event, []).append(callback)
        return self

    def recv(self, timeout: Optional[float] = None) -> Optional[TtsStreamEvent]:
        """Next event, or None when the timeout elapses or the stream is over."""
        if self._closed.is_set() and self._events.empty():
            return None
        try:
            return self._events.get(timeout=timeout)
        except queue.Empty:
            return None

    def __iter__(self) -> Iterator[TtsStreamEvent]:
        while True:
            event = self._events.get()
            if event is None:
                return
            yield event

    def audio_chunks(self, *, close: bool = False) -> Iterator[bytes]:
        """Iterate just the raw PCM frames; ends when the session closes.

        With ``close=True`` (for one-shot flows where all text is already
        submitted) a CloseStream is sent first, so the server synthesizes
        everything pending and the iterator terminates naturally. With the
        default ``close=False`` the session stays open — end it yourself with
        :meth:`close` (e.g. from another thread) or the iterator never ends.
        """
        if close and not self._closed.is_set():
            self._send_control("CloseStream")
        for event in self:
            if isinstance(event, TtsAudioChunk):
                yield event.data

    def stream_to_file(
        self, path: str, *, close: bool = True
    ) -> Optional[TtsSessionEnd]:
        """Write the streamed audio to a WAV file as it arrives, returning the
        session summary once the session ends.

        By default this sends CloseStream first (one-shot flow: submit all
        text, then call this). Pass ``close=False`` when another thread owns
        the session lifecycle.
        """
        if close and not self._closed.is_set():
            self._send_control("CloseStream")
        sample_rate = self._session_begin.sample_rate if self._session_begin else 24000
        with wave.open(path, "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(sample_rate)
            for event in self:
                if isinstance(event, TtsSessionBegin):
                    out.setframerate(event.sample_rate)
                elif isinstance(event, TtsAudioChunk):
                    out.writeframes(event.data)
        return self._session_end

    # -- sending -------------------------------------------------------------

    def send_text(self, text: str, *, id: Optional[str] = None) -> None:
        """Submit text to synthesize — a whole paragraph or incremental
        sentences (type-ahead / LLM output). The server holds back a trailing
        incomplete sentence until more text, finalize() or close() arrives; a
        frame boundary is treated as a word boundary. Max 2000 characters per
        call (``myvoicemaker.chunk_text`` helps split longer text)."""
        frame: dict[str, object] = {"type": "Text", "text": text}
        if id is not None:
            frame["id"] = id
        self._ws.send(json.dumps(frame))

    def finalize(self) -> None:
        """Flush the held-back sentence tail and synthesize everything
        submitted so far, without closing. Acked with a "finalized" event."""
        self._send_control("Finalize")

    def _send_control(self, control_type: str) -> None:
        try:
            self._ws.send(json.dumps({"type": control_type}))
        except Exception:
            pass

    def _keepalive_loop(self) -> None:
        while not self._closed.wait(self._keepalive_interval):
            self._send_control("KeepAlive")

    # -- lifecycle -------------------------------------------------------------

    @property
    def session(self) -> Optional[TtsSessionBegin]:
        return self._session_begin

    @property
    def result(self) -> Optional[TtsSessionEnd]:
        """Session summary; populated once the stream has ended."""
        return self._session_end

    def close(self) -> Optional[TtsSessionEnd]:
        """Gracefully end the session: the server synthesizes and delivers all
        remaining text, sends session.end, then closes."""
        if not self._closed.is_set():
            self._send_control("CloseStream")
            self._closed.wait(timeout=_CLOSE_GRACE_S)
        try:
            self._ws.close()
        except Exception:
            pass
        return self._session_end

    def __enter__(self) -> "TtsStreamConnection":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
