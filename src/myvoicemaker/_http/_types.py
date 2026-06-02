from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class RateLimitHeaders:
    limit: int
    remaining: int
    reset: int


@dataclass
class ApiResponse(Generic[T]):
    data: T
    request_id: str | None
    rate_limit: RateLimitHeaders | None
