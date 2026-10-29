# Changelog

## Unreleased

### Added
- **Four new API error codes** in the catalog (`describe_error_code()`, hints,
  `e.retryable`):
  - `account_suspended` (403, `ForbiddenError`): the account that owns the key
    is suspended; every key and stream token on it is refused.
  - `file_url_host_not_allowed` (400, `ValidationError`): the URL given to
    `asr.transcribe()` or `animate.generate()` resolves or redirects to a
    private, loopback, link-local or otherwise non-public address.
  - `invalid_webhook_url` (400, `ValidationError`): `webhook_url` is not a
    public http(s) URL.
  - `audio_url_unreadable` (422, `ValidationError`): `animate.generate()` could
    not download `audio_url` or read its duration (animations are now priced
    from the real audio length).

  Older SDK versions already raise these as the status-based class with the
  raw code on `e.code`; this adds the descriptions and hints.
- `scripts/sync_error_catalog.py` transliterates `webhookUrl` to `webhook_url`.

## 0.2.0 — 2026-08-26

First release since 0.1.1 (internal iterations 0.2.0–0.5.0 were never
published; this release supersedes them).

### Added
- **Method-aware, code-mapped errors.** Every exception now names the SDK
  method that failed, rewrites endpoint hints into SDK calls, and ends with the
  machine-readable code and request id — e.g.
  `tts.generate(): Unknown voice — … Use tts.list_voices() … [unknown_voice_id · request 8f1c2d3e]`.
  All errors expose `code`, `method`; API errors add `hint`, `description`,
  `retryable`, `retry_after`, and fall back to the `X-Request-Id` header for
  `request_id`.
- Error-code catalog: `ERROR_CODES`, `CLIENT_ERROR_CODES`, `STREAM_ERROR_CODES`,
  `STREAM_CLOSE_CODES`, `describe_error_code()`, `describe_stream_close()`
  (generated from the JS SDK catalog by `scripts/sync_error_catalog.py`).
- Code-specific classes: `StreamTokenError`, `UnknownVoiceError`,
  `VoiceNotReadyError`, `ConcurrencyLimitError`, `QueueLimitError`,
  `StreamConcurrencyError`, `ServiceUnavailableError` (503),
  `ServiceWarmingError` (`tts_warming`).
- Client-side classes replacing bare `ValueError`/`RuntimeError`s:
  `ConfigurationError` (missing api_key / credential / websockets),
  `InvalidArgumentError`, `StreamClosedError`, `NetworkError`,
  `RequestTimeoutError`.
- Streaming: a refused WebSocket upgrade now raises the same typed exception a
  REST call would (the handshake's JSON error body is parsed) instead of a raw
  `websockets.InvalidStatus`; `send_audio()`/`send_text()` on a closed stream
  raise `StreamClosedError`; `conn.error` keeps a transport failure.
- Async TTS: `tts.generate(..., mode="async")` returns a `TtsJobResponse`;
  `tts.get_result(id)` and `tts.poll(id)` fetch it (`TtsResultResponse`).
- **Real-time TTS streaming** — `client.tts.stream()` (`wss /dev/v1/tts/stream`,
  chunk-level events, mono PCM16LE @ 24 kHz) via `TtsStreamConnection`, plus
  the `chunk_text()` sentence chunker.
- **Real-time ASR streaming** — `client.asr.stream()`
  (`wss /dev/v1/transcribe/stream`, interim + final transcripts) via
  `AsrStreamConnection`.
- **Ephemeral stream tokens** — `client.auth.create_stream_token()` mints
  single-use `vmst_*` tokens; both stream methods accept `access_token` so
  untrusted clients can stream without the API key.
- **Custom voices** — `tts.generate()`/`tts.stream()` accept your own cloned
  voice ids; `Voice.type` (`"preset"`/`"custom"`) on listings; `voice_not_ready`
  surfaces as a 422.
- **Output formats** — `tts.generate()` `output_format` `"wav"`/`"mp3"`/`"ogg"`
  (real conversion server-side), echoed on the response.
- `client.tts.list_languages()` — discover the currently enabled TTS
  languages (`GET /dev/v1/tts/languages`), including per-language capability
  flags and the platform's `default_language`. The catalog is
  admin-configured and can change at runtime.
- `UnsupportedLanguageError` (subclass of `ValidationError`) — raised when
  the requested language is not in the platform catalog or is not available
  for the operation (`error_code: "unsupported_language"` /
  `"streaming_unsupported_language"`).
- `error_code` is now parsed from API error bodies and exposed on
  `VoiceMakerAPIError`.
- New types: `TtsLanguage`, `TtsLanguageListResponse`, `KnownLanguage`.

### Changed
- `PermissionError` is renamed `ForbiddenError` and `TimeoutError` is renamed
  `PollTimeoutError` (aliases kept and deprecated): both old names shadowed
  Python builtins when imported.
- Unmapped 4xx statuses now surface as the base `VoiceMakerAPIError` instead
  of `ServerError`; 503 is `ServiceUnavailableError`.
- Non-JSON error responses (proxy pages, wrong `base_url`) still produce a
  typed exception with code `http_<status>`.

### Fixed
- Every 429 response raised `TypeError` (`RateLimitError.__init__` did not
  accept `error_code`) instead of `RateLimitError`.
- **`tts.stream()` no longer defaults `language` to `"auto"`.** Omitted, the
  language is now resolved server-side to the platform's default. Pass
  `language="auto"` explicitly to pin it.
- `tts.generate()`'s `language` is now optional (same server-side default).
- `SupportedLanguage` is now `str` (the catalog is server-configured, so a
  compiled-in `Literal` can no longer be exhaustive). The old union is kept
  as `KnownLanguage` for reference.
- HTTP 400 responses now map to `ValidationError` (previously the generic
  `ServerError`).
- Yoruba (`yo`) and Igbo (`ig`) are now first-class languages server-side
  (previously aliases of `auto`) and can be streamed.
