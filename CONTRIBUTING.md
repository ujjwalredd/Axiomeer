# Contributing to Axiomeer

Thanks for taking the time to contribute. This guide covers the basics for
new contributors. The project is Apache 2.0 licensed and welcomes
contributions of all sizes — bug fixes, new providers, docs, tests.

## Quick start

```bash
git clone https://github.com/ujjwalredd/Axiomeer.git
cd Axiomeer
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,observability,redis]"

# Run tests
pytest -q

# Lint
ruff check .
```

## Running the API locally

```bash
cp .env.example .env
# Set DB_PASSWORD and JWT_SECRET_KEY (32+ chars) in .env
docker-compose up -d
curl http://localhost:8000/health
```

## Project layout

```
apps/api/               FastAPI application (routers, middleware, observability)
src/marketplace/        Core library: router, executor, auth, storage, LLM
sdk/python/             Public Python SDK (pip install axiomeer)
sdk/javascript/         Public TypeScript SDK
manifests/              Provider manifests (JSON) — one file per API
alembic/                Database migrations
tests/                  Pytest suite
scripts/                Operational scripts (manifest validation, fixes)
```

## Adding a new provider manifest

1. Create `manifests/categories/<category>/<id>.json` following the existing
   shape. Required fields: `id`, `name`, `description`, `capabilities`,
   `executor_url`. See `src/marketplace/core/models.py` (`AppCreate`) for the
   full schema.
2. Validate: `python scripts/validate_manifests.py`
3. The CI workflow runs this automatically on every PR.

## Submitting changes

1. Fork, create a feature branch off `main`.
2. Write code + tests. CI must pass: ruff + pytest + manifest validation.
3. Open a PR with a clear description and link to any related issue.
4. Maintainers will review. Small, focused PRs land faster.

## Security

Do **not** open public issues for security vulnerabilities. Email or
disclose privately per [SECURITY.md](SECURITY.md).

## Code style

- Ruff is the source of truth; configuration in `pyproject.toml`.
- Type hints encouraged on new code; mypy runs in advisory mode.
- No comments that restate the code — comments explain *why*, not *what*.
- Keep functions small. Prefer composition over flags.

## Tests

- Unit tests in `tests/test_*.py` should not require network or Docker.
- Tests that need network should be marked `@pytest.mark.integration` and
  skipped by default in CI.
- New routes need at least one happy-path test.
- Security-sensitive code (auth, SSRF validator, idempotency) needs a
  regression test alongside the fix.

## Releasing

Maintainers cut releases via Git tags. Versions follow SemVer; breaking API
changes require a new `/v2` namespace, not a major bump alone.
