from __future__ import annotations

from ._http._client import HttpClient
from ._modules._asr import ASRModule
from ._modules._tts import TTSModule
from ._modules._animate import AnimateModule
from ._modules._explain import ExplainModule
from ._modules._usage import UsageModule

_DEFAULT_BASE_URL = "https://api.myvoicemaker.ai"
_DEFAULT_TIMEOUT = 30.0


class VoiceMaker:
    tts: TTSModule
    asr: ASRModule
    animate: AnimateModule
    explain: ExplainModule
    usage: UsageModule

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")

        http = HttpClient(api_key=api_key, base_url=base_url, timeout=timeout)
        self.tts = TTSModule(http)
        self.asr = ASRModule(http)
        self.animate = AnimateModule(http)
        self.explain = ExplainModule(http)
        self.usage = UsageModule(http)

    def close(self) -> None:
        self.tts._http.close()

    def __enter__(self) -> VoiceMaker:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
