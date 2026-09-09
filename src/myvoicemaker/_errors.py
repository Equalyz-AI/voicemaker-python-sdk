"""Typed exceptions raised by the VoiceMaker SDK.

Every error carries a stable machine-readable ``code`` and the SDK ``method``
that raised it, and its message reads like::

    tts.generate(): Unknown voice — voice_id 'foo' does not match an enabled
    voice preset or one of your custom voices. Use tts.list_voices() to see
    the available voices. [unknown_voice_id · request 8f1c2d3e]

See ``ERROR_CODES`` for the full catalog and ``README.md`` for the class tree.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Type

from ._error_catalog import (
    CLIENT_ERROR_CODES,
    ERROR_CODES,
    STREAM_CLOSE_CODES,
    STREAM_ERROR_CODES,
    ErrorCodeInfo,
    describe_error_code,
    describe_stream_close,
)

__all__ = [
    "ERROR_CODES",
    "CLIENT_ERROR_CODES",
    "STREAM_ERROR_CODES",
    "STREAM_CLOSE_CODES",
    "ErrorCodeInfo",
    "describe_error_code",
    "describe_stream_close",
    "rewrite_endpoint_references",
    "format_api_error_message",
    "VoiceMakerError",
    "VoiceMakerAPIError",
    "AuthenticationError",
    "StreamTokenError",
    "InsufficientCreditsError",
    "ForbiddenError",
    "PermissionError",
    "NotFoundError",
    "FileSizeLimitError",
    "UnsupportedMediaTypeError",
    "ValidationError",
    "UnsupportedLanguageError",
    "UnknownVoiceError",
    "VoiceNotReadyError",
    "RateLimitError",
    "ConcurrencyLimitError",
    "QueueLimitError",
    "StreamConcurrencyError",
    "ServiceUnavailableError",
    "ServiceWarmingError",
    "ServerError",
    "ConfigurationError",
    "InvalidArgumentError",
    "StreamClosedError",
    "NetworkError",
    "RequestTimeoutError",
    "PollTimeoutError",
    "TimeoutError",
    "create_api_error",
]

# Server messages are written for REST consumers and reference raw endpoints.
# Rewrite those into the SDK method that wraps them so a developer reading the
# message knows exactly what to call.
_ENDPOINT_REWRITES = [
    (re.compile(r"(?:GET\s+)?/dev/v1/tts/voices\b"), "tts.list_voices()"),
    (re.compile(r"(?:GET\s+)?/dev/v1/tts/languages\b"), "tts.list_languages()"),
    (re.compile(r"(?:POST\s+)?/dev/v1/auth/stream-token\b"), "auth.create_stream_token()"),
    (re.compile(r"(?:GET\s+)?/dev/v1/tts/:id\b"), "tts.get_result()"),
    (re.compile(r"(?:POST\s+)?/dev/v1/tts/generate\b"), "tts.generate()"),
    (re.compile(r"(?:wss?://[^\s/]*)?/dev/v1/tts/stream\b"), "tts.stream()"),
    (re.compile(r"(?:wss?://[^\s/]*)?/dev/v1/transcribe/stream\b"), "asr.stream()"),
    (re.compile(r"(?:GET\s+)?/dev/v1/transcribe/:job_id\b"), "asr.get_result()"),
    (re.compile(r"(?:POST\s+)?/dev/v1/transcribe\b"), "asr.transcribe()"),
    (re.compile(r"(?:GET\s+)?/dev/v1/transcriptions\b"), "asr.list()"),
    (re.compile(r"(?:POST\s+)?/dev/v1/animate/generate\b"), "animate.generate()"),
    (re.compile(r"(?:GET\s+)?/dev/v1/animate/:job_id\b"), "animate.get_result()"),
    (re.compile(r"(?:POST\s+)?/dev/v1/explain\b"), "explain.process()"),
    (re.compile(r"(?:GET\s+)?/dev/v1/usage/breakdown\b"), "usage.get_breakdown()"),
    (re.compile(r"(?:GET\s+)?/dev/v1/usage\b"), "usage.get_balance()"),
    (re.compile(r'\bmode:"async"'), 'mode="async"'),
]

_SDK_METHOD_REFERENCE = re.compile(r"\b[a-z]+\.[a-z_]+\(\)")


def rewrite_endpoint_references(text: str) -> str:
    """Rewrite raw endpoint references in an API message into SDK method calls."""
    for pattern, replacement in _ENDPOINT_REWRITES:
        text = pattern.sub(replacement, text)
    return text


def format_api_error_message(
    *,
    status: int,
    title: str,
    detail: Optional[str] = None,
    code: Optional[str] = None,
    request_id: Optional[str] = None,
    method: Optional[str] = None,
    hint: Optional[str] = None,
) -> str:
    """Build the message for an API error (see the module docstring).

    The catalog hint is appended only when the (rewritten) server detail does
    not already tell the developer which SDK method to call.
    """
    detail_text = rewrite_endpoint_references(detail.strip()) if detail else ""
    head = f"{method}(): {title}" if method else title
    if detail_text and detail_text != title:
        head = f"{head} — {detail_text}"
    parts = [head]
    if hint and not _SDK_METHOD_REFERENCE.search(detail_text):
        parts.append(hint)
    tag = [code or f"http_{status}"]
    if request_id:
        tag.append(f"request {request_id[:8]}")
    parts.append(f"[{' · '.join(tag)}]")
    return " ".join(parts)


def _format_client_message(method: Optional[str], text: str, code: str) -> str:
    prefix = f"{method}(): " if method else ""
    return f"{prefix}{text} [{code}]"


class VoiceMakerError(Exception):
    """Base class for everything this SDK raises.

    ``code`` is always set — an API code (``ERROR_CODES``), a client-side code
    (``CLIENT_ERROR_CODES``) or ``http_<status>`` for an API response without
    one. ``method`` names the SDK call that raised it, e.g. ``"tts.generate"``.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str = "unknown",
        method: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.method = method


class VoiceMakerAPIError(VoiceMakerError):
    """Raised for every non-2xx API response. Subclasses refine by status and code."""

    #: Status used when the constructor is not given one.
    default_status: int = 500

    def __init__(
        self,
        status: Optional[int] = None,
        error: str = "",
        detail: str = "",
        request_id: Optional[str] = None,
        issues: Optional[List[Dict[str, str]]] = None,
        error_code: Optional[str] = None,
        *,
        method: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> None:
        status = self.default_status if status is None else status
        info = describe_error_code(error_code) if error_code else None
        code = error_code or f"http_{status}"
        title = error or (info.title if info else f"HTTP {status}")
        super().__init__(
            format_api_error_message(
                status=status,
                title=title,
                detail=detail,
                code=code,
                request_id=request_id,
                method=method,
                hint=info.hint if info else None,
            ),
            code=code,
            method=method,
        )
        #: HTTP status code.
        self.status = status
        #: Short title from the API (``error`` field).
        self.error = title
        #: Explanation from the API, with endpoint references rewritten to SDK methods.
        self.detail = rewrite_endpoint_references(detail) if detail else ""
        #: Request id for support, from the body or the ``X-Request-Id`` header.
        self.request_id = request_id
        #: Field-level validation issues (400/422 only).
        self.issues = issues
        #: Raw ``errorCode`` from the response body (None when the API sent none).
        self.error_code = error_code
        #: Seconds to wait before retrying, when the API sent ``Retry-After``.
        self.retry_after = retry_after
        #: Whether repeating the same call later can succeed without changes.
        self.retryable = info.retryable if info else (status == 429 or status >= 500)
        #: What the code means, from the catalog (empty for unknown codes).
        self.description = info.description if info else ""
        #: What to do about it, in SDK terms (empty for unknown codes).
        self.hint = info.hint if info else ""


class AuthenticationError(VoiceMakerAPIError):
    """401 — missing, invalid or expired API key (or stream token)."""

    default_status = 401


class StreamTokenError(AuthenticationError):
    """An ephemeral stream token was rejected: invalid, expired, already used
    (401 ``invalid_stream_token``) or minted for the other stream kind
    (403 ``stream_token_kind_mismatch``). Mint a fresh one with
    ``auth.create_stream_token()`` right before connecting."""


class InsufficientCreditsError(VoiceMakerAPIError):
    """402 — not enough purchased credits."""

    default_status = 402


class ForbiddenError(VoiceMakerAPIError):
    """403 — key revoked, project disabled, plan without API access, or missing scope."""

    default_status = 403


#: Deprecated alias of :class:`ForbiddenError`. Importing it shadows Python's
#: builtin ``PermissionError`` — prefer ``ForbiddenError``. Removed in 1.0.
PermissionError = ForbiddenError


class NotFoundError(VoiceMakerAPIError):
    """404 — no such job for this project, or no such endpoint (check base_url)."""

    default_status = 404


class FileSizeLimitError(VoiceMakerAPIError):
    """413 — the audio file exceeds the plan's (or the endpoint's) size limit."""

    default_status = 413


class UnsupportedMediaTypeError(VoiceMakerAPIError):
    """415 — unsupported media format or request content type."""

    default_status = 415


class ValidationError(VoiceMakerAPIError):
    """400/422 — the request was understood but its values were rejected; see ``issues``."""

    default_status = 422


class UnsupportedLanguageError(ValidationError):
    """The requested language is not in the platform's (admin-configured)
    language catalog, or is not available for the requested operation —
    e.g. streaming. Call ``client.tts.list_languages()`` for the current set."""

    default_status = 400


class UnknownVoiceError(ValidationError):
    """422 ``unknown_voice_id`` — the voice id matches neither a preset nor one of your clones."""


class VoiceNotReadyError(ValidationError):
    """422 ``voice_not_ready`` — the custom voice exists but cannot synthesise yet."""


class RateLimitError(VoiceMakerAPIError):
    """429 — request rate, queue, concurrency or stream limits. ``retry_after`` says how long to wait."""

    default_status = 429


class ConcurrencyLimitError(RateLimitError):
    """429 ``concurrency_limit_reached`` — the plan's processing-job cap is in use (sync TTS)."""


class QueueLimitError(RateLimitError):
    """429 ``queue_limit_reached`` — too many of your jobs are already queued."""


class StreamConcurrencyError(RateLimitError):
    """429 ``stream_concurrency_limit`` — the plan's concurrent-stream cap is in use."""


class ServiceUnavailableError(VoiceMakerAPIError):
    """503 — a dependency is temporarily unavailable; retry later (``retry_after`` when sent)."""

    default_status = 503


class ServiceWarmingError(ServiceUnavailableError):
    """503 ``tts_warming`` — the speech engine is cold-starting; retry in ~``retry_after``s or use ``mode="async"``."""


class ServerError(VoiceMakerAPIError):
    """5xx other than 503 — the server failed while processing; usually retryable."""

    default_status = 500


# ---- client-side errors (no HTTP exchange) ------------------------------------


def _client_message(code: str, method: Optional[str], detail: Optional[str] = None) -> str:
    info = CLIENT_ERROR_CODES[code]
    text = (
        f"{info.title} — {detail} {info.hint}"
        if detail
        else f"{info.title} — {info.description} {info.hint}"
    )
    return _format_client_message(method, text, code)


class ConfigurationError(VoiceMakerError):
    """The client is missing something it needs before it can make the call
    (API key, stream credential, the ``websockets`` package)."""

    def __init__(self, code: str, method: Optional[str] = None) -> None:
        super().__init__(_client_message(code, method), code=code, method=method)


class InvalidArgumentError(VoiceMakerError):
    """An argument failed validation in the SDK, before any request was made."""

    def __init__(self, argument: str, detail: str, method: Optional[str] = None) -> None:
        super().__init__(
            _client_message("invalid_argument", method, f"{argument}: {detail}"),
            code="invalid_argument",
            method=method,
        )
        #: Name of the offending argument.
        self.argument = argument


class StreamClosedError(VoiceMakerError):
    """``send_audio()``/``send_text()`` was called on a stream that is not open."""

    def __init__(self, method: Optional[str] = None) -> None:
        super().__init__(
            _client_message("stream_not_open", method), code="stream_not_open", method=method
        )


class NetworkError(VoiceMakerError):
    """The request never reached the API (DNS, connection refused, TLS, proxy, offline)."""

    def __init__(self, method: Optional[str], cause: BaseException) -> None:
        reason = str(cause) or cause.__class__.__name__
        super().__init__(
            _client_message("network_error", method, reason), code="network_error", method=method
        )
        self.__cause__ = cause


class RequestTimeoutError(VoiceMakerError):
    """The API did not answer within the client's ``timeout``."""

    def __init__(self, method: Optional[str], timeout_seconds: float) -> None:
        super().__init__(
            _client_message(
                "request_timeout", method, f"no response within {timeout_seconds:g}s."
            ),
            code="request_timeout",
            method=method,
        )
        self.timeout_seconds = timeout_seconds


class PollTimeoutError(VoiceMakerError):
    """``poll()`` gave up before the job reached a terminal status. The job itself keeps running."""

    def __init__(
        self, job_id: str, timeout_seconds: float, method: Optional[str] = None
    ) -> None:
        super().__init__(
            _client_message(
                "poll_timeout",
                method,
                f"job '{job_id}' did not complete within {timeout_seconds:g}s.",
            ),
            code="poll_timeout",
            method=method,
        )
        self.job_id = job_id
        self.timeout_seconds = timeout_seconds


#: Deprecated alias of :class:`PollTimeoutError`. Importing it shadows Python's
#: builtin ``TimeoutError`` — prefer ``PollTimeoutError``. Removed in 1.0.
TimeoutError = PollTimeoutError


# ---- mapping --------------------------------------------------------------------

_CODE_CLASSES: Dict[str, Type[VoiceMakerAPIError]] = {
    "invalid_stream_token": StreamTokenError,
    "stream_token_kind_mismatch": StreamTokenError,
    "unsupported_language": UnsupportedLanguageError,
    "streaming_unsupported_language": UnsupportedLanguageError,
    "unknown_voice_id": UnknownVoiceError,
    "voice_not_ready": VoiceNotReadyError,
    "concurrency_limit_reached": ConcurrencyLimitError,
    "queue_limit_reached": QueueLimitError,
    "stream_concurrency_limit": StreamConcurrencyError,
    "tts_warming": ServiceWarmingError,
}

_STATUS_CLASSES: Dict[int, Type[VoiceMakerAPIError]] = {
    400: ValidationError,
    401: AuthenticationError,
    402: InsufficientCreditsError,
    403: ForbiddenError,
    404: NotFoundError,
    413: FileSizeLimitError,
    415: UnsupportedMediaTypeError,
    422: ValidationError,
    429: RateLimitError,
    503: ServiceUnavailableError,
}


def create_api_error(
    status: int,
    body: Dict[str, Any],
    retry_after: Optional[str] = None,
    *,
    method: Optional[str] = None,
    request_id: Optional[str] = None,
) -> VoiceMakerAPIError:
    """Turn an API error response into the most specific error class: by
    ``errorCode`` first, then by HTTP status. Unknown codes still get the
    status-based class with the raw code on ``e.code``.

    ``request_id`` is the ``X-Request-Id`` header, used when the body has none.
    """
    error = body.get("error") or f"HTTP {status}"
    detail = body.get("detail") or ""
    error_code = body.get("errorCode")
    issues = body.get("issues")

    parsed_retry: Optional[int] = None
    if retry_after not in (None, ""):
        try:
            parsed_retry = int(float(str(retry_after)))
        except ValueError:
            parsed_retry = None

    cls: Optional[Type[VoiceMakerAPIError]] = None
    if isinstance(error_code, str):
        cls = _CODE_CLASSES.get(error_code)
    if cls is None:
        cls = _STATUS_CLASSES.get(status)
    if cls is None:
        cls = ServerError if status >= 500 else VoiceMakerAPIError

    return cls(
        status,
        error,
        detail,
        body.get("requestId") or request_id,
        issues if isinstance(issues, list) else None,
        error_code if isinstance(error_code, str) else None,
        method=method,
        retry_after=parsed_retry,
    )
