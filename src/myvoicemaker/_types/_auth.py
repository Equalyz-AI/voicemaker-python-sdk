from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

StreamTokenType = Literal["asr", "tts"]


@dataclass
class StreamTokenResponse:
    """Ephemeral, single-use credential for opening a streaming WebSocket.

    Pass ``token`` as ``access_token`` when calling ``asr.stream()`` /
    ``tts.stream()`` from a client that must not hold the real API key.
    """

    token: str
    expires_at: str
    expires_in: int
    type: StreamTokenType

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StreamTokenResponse:
        return cls(
            token=data["token"],
            expires_at=data["expires_at"],
            expires_in=data["expires_in"],
            type=data["type"],
        )
