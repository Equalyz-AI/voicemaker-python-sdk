from __future__ import annotations

from ._base import BaseModule
from .._types._usage import UsageBalanceResponse, UsageBreakdownResponse


class UsageModule(BaseModule):
    def get_balance(self) -> UsageBalanceResponse:
        resp = self._http.get("/dev/v1/usage")
        return UsageBalanceResponse.from_dict(resp.data)

    def get_breakdown(
        self,
        start_date: str,
        end_date: str,
        *,
        module: str | None = None,
    ) -> UsageBreakdownResponse:
        params: dict[str, object] = {
            "start_date": start_date,
            "end_date": end_date,
        }
        if module is not None:
            params["module"] = module

        resp = self._http.get("/dev/v1/usage/breakdown", params)
        return UsageBreakdownResponse.from_dict(resp.data)
