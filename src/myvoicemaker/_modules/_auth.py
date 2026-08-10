from __future__ import annotations

from ._base import BaseModule
from .._types._auth import StreamTokenResponse, StreamTokenType


class AuthModule(BaseModule):
    def create_stream_token(
        self,
        *,
        type: StreamTokenType,
        expires_in: "int | None" = None,
    ) -> StreamTokenResponse:
        """Mint a short-lived, single-use stream token.

        Call this on your backend (where the API key lives) right before an
        untrusted client connects, hand it the ``token``, and have it stream
        with ``access_token=token`` instead of an ``api_key``. Tokens expire
        after ``expires_in`` seconds (10–300, default 60), are consumed on
        first connect, and are scoped to one stream kind (``asr`` or ``tts``).
        """
        body: dict[str, object] = {"type": type}
        if expires_in is not None:
            body["expires_in"] = expires_in
        resp = self._http.post("/dev/v1/auth/stream-token", body)
        return StreamTokenResponse.from_dict(resp.data)
