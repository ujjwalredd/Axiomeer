#!/usr/bin/env python3
"""
Sign bundled manifests with MANIFEST_SIGNING_KEY.

Usage:
    MANIFEST_SIGNING_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))') \
        python scripts/sign_manifests.py

Writes manifests/MANIFESTS.sig. Run this in CI on release builds; consumers
verify on startup by setting the same MANIFEST_SIGNING_KEY env var.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from marketplace.core.manifest_signing import write_signature  # noqa: E402


def main() -> int:
    key = os.getenv("MANIFEST_SIGNING_KEY", "").strip()
    if not key:
        print("MANIFEST_SIGNING_KEY env var is required", file=sys.stderr)
        return 2

    manifests_dir = Path(__file__).resolve().parent.parent / "manifests"
    out = write_signature(manifests_dir, key.encode("utf-8"))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
