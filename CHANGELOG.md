# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Modular API layout**: split the 1636-line `apps/api/main.py` into
  router modules under `apps/api/routers/` (apps, shop, execute, runs, trust,
  messages, capabilities, providers_inline, health) + shared
  `apps/api/services.py`, `apps/api/dependencies.py`, `apps/api/bootstrap.py`,
  `apps/api/lifespan.py`. `main.py` is now ~100 lines of composition.
- **`/v1/` versioned namespace** mirroring all primary routes. Unprefixed
  paths remain for back-compat with existing SDK clients.
- **Per-host circuit breaker** (`marketplace.core.circuit_breaker`) wrapping
  `execute_http` / `execute_http_sync`. Configurable via
  `CB_FAILURE_THRESHOLD`, `CB_RESET_AFTER_SECONDS`.
- **Durable workflow execution**: `POST /execute/workflow/async` launches a
  workflow in the background and returns a `workflow_id`. Poll status at
  `GET /workflows/{workflow_id}` (status, progress, final output). State is
  cache-backed (Redis when configured) with a 24h TTL.
- **Auto-quarantine**: background task scans recent run history and adds
  providers with a sliding-window success rate below
  `QUARANTINE_SUCCESS_FLOOR` to a quarantine set; `/shop` filters those out
  before ranking.
- **Manifest signing**: `scripts/sign_manifests.py` produces
  `manifests/MANIFESTS.sig` (HMAC-SHA256). Boot verifies digests when
  `MANIFEST_SIGNING_KEY` is set; `MANIFEST_VERIFY_MODE=strict` aborts boot
  on mismatch, `warn` (default) logs and continues.
- **Async DB scaffold**: `marketplace.storage.db_async` provides an
  AsyncEngine + `get_async_db` dependency for the Phase 3 migration; see
  `docs/async_db_migration.md` for per-route conversion steps.
- SSRF protection: `validate_safe_url` blocks loopback / RFC1918 / link-local
  / cloud-metadata destinations for outbound provider calls and at manifest
  registration. Trusted-host allowlist via `EXECUTOR_TRUSTED_HOSTS`.
- Request-ID middleware: `X-Request-ID` accepted from clients, generated
  otherwise, echoed in responses, included in error envelopes.
- Security headers middleware (`X-Content-Type-Options`, `X-Frame-Options`,
  HSTS, `Referrer-Policy`, `Permissions-Policy`).
- Consistent JSON error envelope: `{"error": {"code", "message", "request_id", "details"}}`.
- Prometheus metrics endpoint at `/metrics/prom` (opt-in via
  `pip install -e .[observability]`).
- Idempotency-Key middleware: replays cached responses for unsafe methods.
- Shared `httpx.AsyncClient` for outbound provider calls.
- SDK: typed exception hierarchy with `request_id`, `code`, `status_code`,
  `details`. New `PermissionError`, `ConflictError`, `ValidationError`,
  `ServerError`, `NetworkError`, `TimeoutError`.
- CI workflow: ruff, pytest matrix (3.10/3.11/3.12), manifest validation.
- Contributor docs: `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`,
  issue templates, PR template, this changelog.

### Changed
- `AUTH_ENABLED` defaults to `true`. Set `AUTH_ENABLED=false` explicitly for
  local demos.
- CORS middleware now disables `allow_credentials` when origins is `"*"` to
  satisfy CORS spec; exposes `X-Request-ID`.
- DB engine uses `pool_pre_ping`, configurable `pool_size`/`max_overflow`.

### Removed
- Duplicate / backup files: `cache 2.py`, `executor 2.py`, `routers/v1 2.py`,
  `routers/__init__ 2.py`, `scripts/validate_manifests 2.py`,
  `apps/api/providers.py.backup`.
