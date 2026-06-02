from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ._common import AccountTier, UsageModule


@dataclass
class UsageBalanceResponse:
    account_id: str
    tier: AccountTier
    credits_remaining: int
    credits_used: int
    credits_expire: str | None
    created_at: str
    credits_total: int | None = field(default=None)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UsageBalanceResponse:
        return cls(
            account_id=data["account_id"],
            tier=data["tier"],
            credits_remaining=data["credits_remaining"],
            credits_used=data["credits_used"],
            credits_expire=data.get("credits_expire"),
            created_at=data["created_at"],
            credits_total=data.get("credits_total"),
        )


@dataclass
class UsageBreakdownEntry:
    module: UsageModule
    requests: int
    credits_used: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UsageBreakdownEntry:
        return cls(
            module=data["module"],
            requests=data["requests"],
            credits_used=data["credits_used"],
        )


@dataclass
class UsageBreakdownResponse:
    breakdown: list[UsageBreakdownEntry]
    total_requests: int
    total_credits_used: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UsageBreakdownResponse:
        return cls(
            breakdown=[UsageBreakdownEntry.from_dict(e) for e in data["breakdown"]],
            total_requests=data["total_requests"],
            total_credits_used=data["total_credits_used"],
        )
