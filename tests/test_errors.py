"""Offline tests for the error catalog, class mapping and messages (no network)."""

from __future__ import annotations

import json
import re

import httpx
import pytest

import myvoicemaker
from myvoicemaker import (
    CLIENT_ERROR_CODES,
    ERROR_CODES,
    STREAM_ERROR_CODES,
    AuthenticationError,
    ConcurrencyLimitError,
    ConfigurationError,
    ForbiddenError,
    InsufficientCreditsError,
    InvalidArgumentError,
    NetworkError,
    NotFoundError,
    PermissionError,
    PollTimeoutError,
    QueueLimitError,
    RateLimitError,
    RequestTimeoutError,
    ServerError,
    ServiceUnavailableError,
    ServiceWarmingError,
    StreamConcurrencyError,
    StreamTokenError,
    TimeoutError,
    UnknownVoiceError,
    UnsupportedLanguageError,
    ValidationError,
    VoiceMaker,
    VoiceMakerAPIError,
    VoiceMakerError,
    VoiceNotReadyError,
    create_api_error,
    describe_error_code,
    describe_stream_close,
    format_api_error_message,
    rewrite_endpoint_references,
)


def body(error_code=None, *, error="Some title", detail="Some detail.", request_id=None):
    data = {"error": error, "detail": detail}
    if error_code:
        data["errorCode"] = error_code
    if request_id:
        data["requestId"] = request_id
    return data


class TestCatalog:
    def test_every_api_code_is_complete(self) -> None:
        for code, info in ERROR_CODES.items():
            assert info.status >= 400, code
            assert info.title and info.description and info.hint, code
            assert isinstance(info.retryable, bool), code

    def test_hints_use_python_method_names_never_endpoints(self) -> None:
        camel = re.compile(r"\b[a-z]+\.[a-z]+[A-Z][A-Za-z]*\(")
        for table in (ERROR_CODES, CLIENT_ERROR_CODES, STREAM_ERROR_CODES):
            for code, info in table.items():
                assert "/dev/v1" not in info.hint, code
                assert "/dev/v1" not in info.description, code
                assert not camel.search(info.hint), (code, info.hint)

    def test_describe_lookups(self) -> None:
        assert describe_error_code("unknown_voice_id").status == 422
        assert describe_error_code("api_key_required").title == "API key required"
        assert describe_error_code("idle_timeout").retryable is True
        assert describe_error_code("nope") is None
        assert "credits" in describe_stream_close(4002).lower()
        assert "9999" in describe_stream_close(9999)

    def test_catalog_matches_javascript_sdk(self) -> None:
        # The JS catalog is the source of truth; scripts/sync_error_catalog.py
        # regenerates ours. Guard against drift when both repos are checked out.
        from pathlib import Path

        js = Path(__file__).resolve().parents[2] / "sdk" / "src" / "errors" / "catalog.ts"
        if not js.exists():
            pytest.skip("JS SDK checkout not present")
        src = js.read_text()
        js_codes = set(re.findall(r"^  ([a-z_]+): \{$", src, re.M))
        py_codes = set(ERROR_CODES) | set(CLIENT_ERROR_CODES) | set(STREAM_ERROR_CODES)
        assert js_codes == py_codes


class TestRewrite:
    def test_endpoints_become_sdk_methods(self) -> None:
        assert (
            rewrite_endpoint_references("Use GET /dev/v1/tts/voices for the list of available voices.")
            == "Use tts.list_voices() for the list of available voices."
        )
        assert (
            rewrite_endpoint_references("Mint a fresh one via POST /dev/v1/auth/stream-token.")
            == "Mint a fresh one via auth.create_stream_token()."
        )
        assert rewrite_endpoint_references(
            'Retry in ~1 minute, or submit with mode:"async" to queue the job and poll GET /dev/v1/tts/:id.'
        ) == 'Retry in ~1 minute, or submit with mode="async" to queue the job and poll tts.get_result().'
        assert (
            rewrite_endpoint_references("POST /dev/v1/transcribe then GET /dev/v1/transcribe/:job_id")
            == "asr.transcribe() then asr.get_result()"
        )


class TestCreateApiError:
    @pytest.mark.parametrize(
        "code,status,cls",
        [
            ("invalid_stream_token", 401, StreamTokenError),
            ("stream_token_kind_mismatch", 403, StreamTokenError),
            ("unsupported_language", 400, UnsupportedLanguageError),
            ("streaming_unsupported_language", 400, UnsupportedLanguageError),
            ("unknown_voice_id", 422, UnknownVoiceError),
            ("voice_not_ready", 422, VoiceNotReadyError),
            ("concurrency_limit_reached", 429, ConcurrencyLimitError),
            ("queue_limit_reached", 429, QueueLimitError),
            ("stream_concurrency_limit", 429, StreamConcurrencyError),
            ("tts_warming", 503, ServiceWarmingError),
        ],
    )
    def test_maps_by_code_first(self, code, status, cls) -> None:
        err = create_api_error(status, body(code))
        assert isinstance(err, cls)
        assert err.code == code
        assert err.status == status

    def test_code_classes_keep_status_parents(self) -> None:
        assert isinstance(create_api_error(401, body("invalid_stream_token")), AuthenticationError)
        assert isinstance(create_api_error(422, body("unknown_voice_id")), ValidationError)
        assert isinstance(create_api_error(429, body("queue_limit_reached")), RateLimitError)
        assert isinstance(create_api_error(503, body("tts_warming")), ServiceUnavailableError)

    def test_maps_by_status_otherwise(self) -> None:
        assert isinstance(create_api_error(400, body()), ValidationError)
        assert isinstance(create_api_error(401, body("invalid_api_key")), AuthenticationError)
        assert isinstance(create_api_error(402, body("insufficient_credits")), InsufficientCreditsError)
        assert isinstance(create_api_error(403, body("insufficient_scope")), ForbiddenError)
        assert isinstance(create_api_error(404, body("not_found")), NotFoundError)
        assert isinstance(create_api_error(429, body("rate_limited")), RateLimitError)
        assert isinstance(create_api_error(503, body("stream_capacity")), ServiceUnavailableError)
        assert isinstance(create_api_error(500, body("synthesis_failed")), ServerError)
        assert isinstance(create_api_error(502, body()), ServerError)
        odd = create_api_error(418, body())
        assert type(odd) is VoiceMakerAPIError
        assert odd.code == "http_418"

    def test_unknown_future_code_is_preserved(self) -> None:
        err = create_api_error(400, body("brand_new_code"))
        assert isinstance(err, ValidationError)
        assert err.code == err.error_code == "brand_new_code"
        assert err.hint == ""

    def test_rate_limit_no_longer_crashes_and_parses_retry_after(self) -> None:
        # 0.2.0-dev raised TypeError here (RateLimitError lacked error_code).
        err = create_api_error(429, body("rate_limited"), "17")
        assert isinstance(err, RateLimitError)
        assert err.retry_after == 17
        assert err.retryable is True
        assert create_api_error(402, body("insufficient_credits")).retryable is False

    def test_request_id_header_fallback(self) -> None:
        err = create_api_error(401, body("missing_api_key"), request_id="hdr-1234-5678")
        assert err.request_id == "hdr-1234-5678"
        assert create_api_error(401, body("missing_api_key", request_id="body-1"), request_id="hdr-1").request_id == "body-1"

    @pytest.mark.parametrize(
        "code,status,cls",
        [
            ("account_suspended", 403, ForbiddenError),
            ("file_url_host_not_allowed", 400, ValidationError),
            ("invalid_webhook_url", 400, ValidationError),
            ("audio_url_unreadable", 422, ValidationError),
        ],
    )
    def test_suspension_and_url_safety_codes(self, code, status, cls) -> None:
        assert ERROR_CODES[code].status == status
        err = create_api_error(status, body(code))
        assert isinstance(err, cls)
        assert err.code == code
        assert err.hint == ERROR_CODES[code].hint
        assert err.retryable is False

    def test_aliases(self) -> None:
        assert PermissionError is ForbiddenError
        assert TimeoutError is PollTimeoutError
        assert myvoicemaker.PermissionError is not __builtins__["PermissionError"] if isinstance(__builtins__, dict) else True

    def test_all_errors_are_voicemaker_errors_with_codes(self) -> None:
        for err in (
            create_api_error(500, body()),
            ConfigurationError("api_key_required", "tts.generate"),
            InvalidArgumentError("language", "must be explicit", "asr.stream"),
            PollTimeoutError("job_1", 5.0, "asr.poll"),
        ):
            assert isinstance(err, VoiceMakerError)
            assert err.code


class TestMessages:
    def test_method_first_rewritten_hint_and_tag(self) -> None:
        err = create_api_error(
            422,
            {
                "error": "Unknown voice",
                "detail": "voice_id 'foo' does not match an enabled voice preset or one of your custom voices. Use GET /dev/v1/tts/voices for the list of available voices.",
                "errorCode": "unknown_voice_id",
                "requestId": "8f1c2d3e-4a5b-6c7d-8e9f-0a1b2c3d4e5f",
            },
            method="tts.generate",
        )
        assert str(err) == (
            "tts.generate(): Unknown voice — voice_id 'foo' does not match an enabled voice preset "
            "or one of your custom voices. Use tts.list_voices() for the list of available voices. "
            "[unknown_voice_id · request 8f1c2d3e]"
        )
        assert "/dev/v1" not in err.detail
        assert err.hint == ERROR_CODES["unknown_voice_id"].hint

    def test_catalog_hint_appended_when_detail_has_no_sdk_guidance(self) -> None:
        err = create_api_error(
            402,
            {
                "error": "Insufficient credits",
                "detail": "Not enough purchased credits. Required: 1,500 credits.",
                "errorCode": "insufficient_credits",
                "requestId": "abcdef12-0000",
            },
            method="asr.transcribe",
        )
        assert str(err) == (
            "asr.transcribe(): Insufficient credits — Not enough purchased credits. Required: 1,500 credits. "
            "Buy credits in the dashboard; usage.get_balance() shows the current balance. "
            "[insufficient_credits · request abcdef12]"
        )

    def test_hint_not_duplicated(self) -> None:
        err = create_api_error(
            503,
            {
                "error": "TTS engine warming up",
                "detail": 'The TTS engine is starting up (cold start). Retry in ~1 minute, or submit with mode:"async" to queue the job and poll GET /dev/v1/tts/:id.',
                "errorCode": "tts_warming",
            },
            "60",
            method="tts.generate",
        )
        assert str(err) == (
            'tts.generate(): TTS engine warming up — The TTS engine is starting up (cold start). Retry in ~1 minute, '
            'or submit with mode="async" to queue the job and poll tts.get_result(). [tts_warming]'
        )
        assert str(err).count("tts.get_result()") == 1
        assert err.retry_after == 60

    def test_without_method_or_code(self) -> None:
        assert format_api_error_message(status=502, title="HTTP 502", detail="Bad gateway.") == "HTTP 502 — Bad gateway. [http_502]"

    def test_client_side_messages(self) -> None:
        cfg = ConfigurationError("api_key_required", "usage.get_balance")
        assert str(cfg).startswith("usage.get_balance(): API key required — ")
        assert str(cfg).endswith("[api_key_required]")
        assert cfg.code == "api_key_required" and cfg.method == "usage.get_balance"

        arg = InvalidArgumentError("language", "must be explicit.", "asr.stream")
        assert str(arg).startswith("asr.stream(): Invalid argument — language: must be explicit.")
        assert arg.argument == "language"

        t = PollTimeoutError("job_9", 1.0, "animate.poll")
        assert str(t).startswith("animate.poll(): Poll timeout — job 'job_9' did not complete within 1s.")
        assert t.job_id == "job_9"


# ---- HttpClient integration through httpx.MockTransport ----------------------


def _client_with(handler) -> VoiceMaker:
    client = VoiceMaker(api_key="vmk_test_x")
    http = client.tts._http
    http._client = httpx.Client(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer vmk_test_x"},
        timeout=0.5,
    )
    return client


class TestHttpClient:
    def test_rest_error_names_method_and_maps_code(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                422,
                json={
                    "error": "Unknown voice",
                    "detail": "voice_id 'x' does not match an enabled voice preset or one of your custom voices. Use GET /dev/v1/tts/voices for the list of available voices.",
                    "errorCode": "unknown_voice_id",
                    "requestId": "req-1111-2222",
                },
            )

        client = _client_with(handler)
        with pytest.raises(UnknownVoiceError) as info:
            client.tts.generate("hi", "x")
        err = info.value
        assert err.method == "tts.generate"
        assert str(err).startswith("tts.generate(): Unknown voice — ")
        assert "tts.list_voices()" in str(err)
        assert err.request_id == "req-1111-2222"

    def test_request_id_from_header(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={"error": "Unauthorized", "detail": "The provided developer API key is invalid", "errorCode": "invalid_api_key"},
                headers={"X-Request-Id": "hdr-9999-0000"},
            )

        with pytest.raises(AuthenticationError) as info:
            _client_with(handler).usage.get_balance()
        assert info.value.code == "invalid_api_key"
        assert info.value.request_id == "hdr-9999-0000"
        assert "request hdr-9999" in str(info.value)

    def test_retry_after_on_429(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": "Rate limit exceeded", "detail": "Slow down.", "errorCode": "rate_limited"}, headers={"Retry-After": "12"})

        with pytest.raises(RateLimitError) as info:
            _client_with(handler).asr.get_result("j1")
        assert info.value.retry_after == 12
        assert info.value.method == "asr.get_result"

    def test_non_json_error_body(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="<html>404</html>")

        with pytest.raises(NotFoundError) as info:
            _client_with(handler).animate.get_result("a1")
        assert info.value.code == "http_404"
        assert str(info.value) == "animate.get_result(): HTTP 404 — The server answered 404 Not Found without a JSON error body. [http_404]"

    def test_missing_api_key_is_configuration_error(self) -> None:
        client = VoiceMaker()
        with pytest.raises(ConfigurationError) as info:
            client.tts.list_voices()
        assert info.value.code == "api_key_required"
        assert str(info.value).startswith("tts.list_voices(): API key required")

    def test_transport_failure_is_network_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        with pytest.raises(NetworkError) as info:
            _client_with(handler).explain.process("t", "en", "explain")
        assert info.value.code == "network_error"
        assert isinstance(info.value.__cause__, httpx.ConnectError)
        assert "explain.process(): Network error — connection refused" in str(info.value)

    def test_timeout_is_request_timeout_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        with pytest.raises(RequestTimeoutError) as info:
            _client_with(handler).usage.get_balance()
        assert "usage.get_balance(): Request timeout" in str(info.value)

    def test_unreadable_file_is_invalid_argument(self) -> None:
        client = VoiceMaker(api_key="vmk_test_x")
        with pytest.raises(InvalidArgumentError) as info:
            client.asr.transcribe_file("/definitely/not/here.wav")
        assert info.value.argument == "file_path"
        assert str(info.value).startswith("asr.transcribe_file(): Invalid argument — file_path: cannot read '/definitely/not/here.wav'")

    def test_stream_requires_explicit_language(self) -> None:
        client = VoiceMaker(api_key="vmk_test_x")
        with pytest.raises(InvalidArgumentError) as info:
            client.asr.stream(language="auto")
        assert info.value.method == "asr.stream"
        assert "tts.list_languages()" in str(info.value)

    def test_tts_async_mode(self) -> None:
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen.update(json.loads(request.content))
            return httpx.Response(202, json={"requestId": "r", "id": "v1", "status": "queued", "characters": 2, "credits_reserved": 4, "language": "en", "voice_id": "x", "output_format": "wav", "created_at": "now"})

        job = _client_with(handler).tts.generate("hi", "x", mode="async")
        assert seen["mode"] == "async"
        assert job.status == "queued" and job.credits_reserved == 4


class TestStreamHandshake:
    def test_refused_upgrade_maps_to_typed_error(self) -> None:
        from websockets.datastructures import Headers
        from websockets.exceptions import InvalidStatus
        from websockets.http11 import Response

        from myvoicemaker._modules import _streaming

        payload = json.dumps({"error": "Insufficient credits", "detail": "Streaming requires at least 300 purchased credits (60s reserve block).", "errorCode": "insufficient_credits", "requestId": "ws-req-1"}).encode()
        response = Response(402, "Payment Required", Headers([("Content-Type", "application/json"), ("Retry-After", "5")]), payload)

        def fake_connect(*args, **kwargs):
            raise InvalidStatus(response)

        import websockets.sync.client as wsc

        original = wsc.connect
        wsc.connect = fake_connect  # type: ignore[assignment]
        try:
            with pytest.raises(InsufficientCreditsError) as info:
                _streaming.AsrStreamConnection(url="wss://x/dev/v1/transcribe/stream", api_key="k", method="asr.stream")
        finally:
            wsc.connect = original  # type: ignore[assignment]
        err = info.value
        assert err.method == "asr.stream"
        assert err.code == "insufficient_credits"
        assert err.request_id == "ws-req-1"
        assert err.retry_after == 5
        assert str(err).startswith("asr.stream(): Insufficient credits — Streaming requires at least 300 purchased credits")
        assert "usage.get_balance()" in str(err)

    def test_missing_credential_is_configuration_error(self) -> None:
        from myvoicemaker._modules import _tts_streaming

        with pytest.raises(ConfigurationError) as info:
            _tts_streaming.TtsStreamConnection(url="wss://x", api_key=None, access_token=None)
        assert info.value.code == "credential_required"
        assert str(info.value).startswith("tts.stream(): Credential required")
