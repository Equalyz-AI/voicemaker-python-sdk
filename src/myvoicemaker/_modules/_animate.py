from __future__ import annotations

from ._base import BaseModule
from .._types._animate import AnimateJobResponse, AnimateResultResponse
from .._utils import poll as _poll

_TERMINAL = {"completed", "failed"}


class AnimateModule(BaseModule):
    def generate(
        self,
        image_url: str,
        audio_url: str,
        *,
        output_format: str = "mp4",
    ) -> AnimateJobResponse:
        body: dict[str, object] = {
            "image_url": image_url,
            "audio_url": audio_url,
            "output_format": output_format,
        }
        resp = self._http.post("/dev/v1/animate/generate", body, method="animate.generate")
        return AnimateJobResponse.from_dict(resp.data)

    def get_result(self, job_id: str) -> AnimateResultResponse:
        resp = self._http.get(f"/dev/v1/animate/{job_id}", None, method="animate.get_result")
        return AnimateResultResponse.from_dict(resp.data)

    def poll(
        self,
        job_id: str,
        *,
        interval_seconds: float = 2.0,
        timeout_seconds: float = 120.0,
    ) -> AnimateResultResponse:
        return _poll(
            job_id,
            fn=lambda: self.get_result(job_id),
            is_done=lambda r: r.status in _TERMINAL,
            interval_seconds=interval_seconds,
            timeout_seconds=timeout_seconds,
            method="animate.poll",
        )
