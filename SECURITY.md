# Security Policy

## Supported versions

The latest `main` branch and the most recent tagged release receive security
fixes. Older releases are best-effort.

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security problems.

Email the maintainer at the contact listed on the GitHub profile, or use
GitHub's private security advisory feature:

> https://github.com/ujjwalredd/Axiomeer/security/advisories/new

Include:

- A clear description of the issue and impact.
- Steps to reproduce (or a proof-of-concept).
- The commit hash or version you tested against.
- Your disclosure timeline preferences.

We aim to acknowledge reports within 72 hours and to ship a fix or
mitigation within 30 days for high-severity issues.

## Hardening checklist for deployments

- `AUTH_ENABLED=true` (default).
- `JWT_SECRET_KEY` is a 32+ char random value.
- `RATE_LIMIT_ENABLED=true`.
- `CORS_ALLOWED_ORIGINS` set to a specific origin list — never `*` in
  production.
- `EXECUTOR_TRUSTED_HOSTS` set to *only* the first-party hostnames you
  intentionally expose. The SSRF validator enforces this for outbound calls.
- Database password is not the default, and the DB is not exposed publicly.
- Run behind TLS termination with HSTS (the API already sets the header).

## Known threat boundaries

- The `executor_url` field on `AppCreate` lets authenticated users register
  outbound URLs. The validator at `marketplace.core.executor.validate_safe_url`
  blocks loopback, RFC1918, link-local, and cloud-metadata endpoints unless
  the hostname is in `EXECUTOR_TRUSTED_HOSTS`. Treat this allowlist as
  security-critical.
- The legacy `AUTH_ENABLED=false` mode disables authentication entirely. It
  is intended for local demos and CI fixtures only.
