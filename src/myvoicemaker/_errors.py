from __future__ import annotations

from typing import Any


class VoiceMakerError(Exception):
    pass


class VoiceMakerAPIError(VoiceMakerError):
    def __init__(
        self,
        status: int,
        error: str,
        detail: str,
        request_id: str | None = None,
        issues: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(detail or error)
        self.status = status
        self.error = error
        self.detail = detail
        self.request_id = request_id
        self.issues = issues


class AuthenticationError(VoiceMakerAPIError):
    pass


class InsufficientCreditsError(VoiceMakerAPIError):
    pass


class PermissionError(VoiceMakerAPIError):
    pass


class NotFoundError(VoiceMakerAPIError):
    pass


class FileSizeLimitError(VoiceMakerAPIError):
    pass


class UnsupportedMediaTypeError(VoiceMakerAPIError):
    pass


class ValidationError(VoiceMakerAPIError):
    pass


class RateLimitError(VoiceMakerAPIError):
    def __init__(
        self,
        status: int,
        error: str,
        detail: str,
        request_id: str | None = None,
        issues: list[dict[str, str]] | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(status, error, detail, request_id, issues)
        self.retry_after = retry_after


class ServerError(VoiceMakerAPIError):
    pass


class TimeoutError(VoiceMakerError):
    def __init__(self, job_id: str, timeout_seconds: float) -> None:
        super().__init__(
            f"Job '{job_id}' did not complete within {timeout_seconds}s"
        )
        self.job_id = job_id
        self.timeout_seconds = timeout_seconds


def create_api_error(
    status: int,
    body: dict[str, Any],
    retry_after: str | None = None,
) -> VoiceMakerAPIError:
    error = body.get("error", "Unknown error")
    detail = body.get("detail", str(body))
    request_id = body.get("requestId")
    issues = body.get("issues")

    kwargs: dict[str, Any] = dict(
        status=status,
        error=error,
        detail=detail,
        request_id=request_id,
        issues=issues,
    )

    if status == 401:
        return AuthenticationError(**kwargs)
    if status == 402:
        return InsufficientCreditsError(**kwargs)
    if status == 403:
        return PermissionError(**kwargs)
    if status == 404:
        return NotFoundError(**kwargs)
    if status == 413:
        return FileSizeLimitError(**kwargs)
    if status == 415:
        return UnsupportedMediaTypeError(**kwargs)
    if status == 422:
        return ValidationError(**kwargs)
    if status == 429:
        parsed_retry = int(retry_after) if retry_after is not None else None
        return RateLimitError(**kwargs, retry_after=parsed_retry)
    return ServerError(**kwargs)
