from __future__ import annotations

import json
import queue
import threading
from typing import Callable, Iterator, Optional, Union

from .._types._asr_stream import (
    StreamError,
    StreamSessionBegin,
    StreamSessionEnd,
    StreamTranscript,
)

StreamEvent = Union[StreamSessionBegin, StreamTranscript, StreamSessionEnd, StreamError]

_KEEPALIVE_INTERVAL_S = 10.0
_CLOSE_GRACE_S = 8.0


class AsrStreamConnection:
    """Live transcription session over a WebSocket (sync API).

    Send PCM16LE mono audio with :meth:`send_audio`; consume typed events by
    iterating the connection (or via ``on(...)`` callbacks, which fire on a
    background reader thread). Interim transcripts (``is_final=False``) may be
    revised; finals never change. Use as a context manager for a clean close::

        with client.asr.stream(language="yo") as conn:
            threading.Thread(target=send_chunks, args=(conn,), daemon=True).start()
            for event in conn:
                if isinstance(event, StreamTranscript) and event.is_final:
                    print(event.text)

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
        self._events: "queue.Queue[Optional[StreamEvent]]" = queue.Queue()
        self._callbacks: dict[str, list[Callable[[StreamEvent], None]]] = {}
        self._session_begin: Optional[StreamSessionBegin] = None
        self._session_end: Optional[StreamSessionEnd] = None
        self._closed = threading.Event()
        self._keepalive_interval = max(1.0, keepalive_interval)

        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self._keepalive = threading.Thread(target=self._keepalive_loop, daemon=True)
        self._keepalive.start()

    # -- receiving -----------------------------------------------------------

    def _read_loop(self) -> None:
        try:
            while True:
                raw = self._ws.recv()
                if not isinstance(raw, str):
                    continue
                event = self._parse_event(raw)
                if event is None:
                    continue
                self._dispatch(event)
        except Exception:
            pass
        finally:
            self._closed.set()
            self._events.put(None)

    def _parse_event(self, raw: str) -> Optional[StreamEvent]:
        try:
            data = json.loads(raw)
        except ValueError:
            return None
        event_type = data.get("type")
        if event_type == "session.begin":
            self._session_begin = StreamSessionBegin.from_dict(data)
            return self._session_begin
        if event_type == "transcript":
            return StreamTranscript.from_dict(data)
        if event_type == "session.end":
            self._session_end = StreamSessionEnd.from_dict(data)
            return self._session_end
        if event_type == "error":
            return StreamError.from_dict(data)
        # "finalized" and internal events carry no payload consumers need.
        return None

    def _dispatch(self, event: StreamEvent) -> None:
        name = {
            StreamSessionBegin: "open",
            StreamTranscript: "transcript",
            StreamSessionEnd: "end",
            StreamError: "error",
        }[type(event)]
        for callback in self._callbacks.get(name, []):
            try:
                callback(event)
            except Exception:
                pass
        self._events.put(event)

    def on(self, event: str, callback: Callable[[StreamEvent], None]) -> "AsrStreamConnection":
        """Register a callback for "open", "transcript", "end" or "error".

        Callbacks run on the background reader thread.
        """
        self._callbacks.setdefault(event, []).append(callback)
        return self

    def recv(self, timeout: Optional[float] = None) -> Optional[StreamEvent]:
        """Next event, or None when the timeout elapses or the stream is over."""
        if self._closed.is_set() and self._events.empty():
            return None
        try:
            return self._events.get(timeout=timeout)
        except queue.Empty:
            return None

    def __iter__(self) -> Iterator[StreamEvent]:
        while True:
            event = self._events.get()
            if event is None:
                return
            yield event
            if isinstance(event, StreamSessionEnd):
                # Drain sentinel so a second iteration terminates immediately.
                continue

    # -- sending -------------------------------------------------------------

    def send_audio(self, chunk: bytes) -> None:
        """Send a chunk of PCM16LE mono audio (50-250 ms per chunk works well)."""
        self._ws.send(chunk)

    def finalize(self) -> None:
        """Flush pending words into a final transcript without closing."""
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
    def session(self) -> Optional[StreamSessionBegin]:
        return self._session_begin

    @property
    def result(self) -> Optional[StreamSessionEnd]:
        """Session summary; populated once the stream has ended."""
        return self._session_end

    def close(self) -> Optional[StreamSessionEnd]:
        """Gracefully end the session (server flushes the tail first)."""
        if not self._closed.is_set():
            self._send_control("CloseStream")
            self._closed.wait(timeout=_CLOSE_GRACE_S)
        try:
            self._ws.close()
        except Exception:
            pass
        return self._session_end

    def __enter__(self) -> "AsrStreamConnection":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
