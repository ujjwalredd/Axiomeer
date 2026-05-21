"""
Manifest signing and verification.

Goal: detect tampering of bundled manifests between release and boot. A
release-time script computes a SHA-256 digest of each manifest file's
canonical-form bytes, signs the digest table with HMAC-SHA256 using a release
key, and writes `manifests/MANIFESTS.sig`. On boot, the API verifies the
table and refuses to load tampered manifests (configurable: warn vs fail).

This is intentionally simple (HMAC, not asymmetric) because manifests ship
inside the repository; the threat we mitigate is post-clone modification on
the deploy host or in-flight tampering of a release artifact.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

SIG_FILENAME = "MANIFESTS.sig"


def _key_bytes() -> bytes | None:
    raw = os.getenv("MANIFEST_SIGNING_KEY", "").strip()
    if not raw:
        return None
    return raw.encode("utf-8")


def _canonical_bytes(path: Path) -> bytes:
    """Round-trip JSON to canonicalize whitespace before hashing."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _manifest_paths(manifests_dir: Path) -> list[Path]:
    return sorted(
        list(manifests_dir.glob("*.json"))
        + list(manifests_dir.glob("categories/*/*.json"))
    )


def compute_digests(manifests_dir: Path) -> dict[str, str]:
    """Map relative-path -> sha256 hex digest for every manifest."""
    out: dict[str, str] = {}
    for p in _manifest_paths(manifests_dir):
        rel = p.relative_to(manifests_dir).as_posix()
        out[rel] = hashlib.sha256(_canonical_bytes(p)).hexdigest()
    return out


def sign(manifests_dir: Path, key: bytes) -> dict:
    digests = compute_digests(manifests_dir)
    table = json.dumps(digests, sort_keys=True, separators=(",", ":")).encode("utf-8")
    mac = hmac.new(key, table, hashlib.sha256).hexdigest()
    return {"version": 1, "digests": digests, "hmac": mac}


def write_signature(manifests_dir: Path, key: bytes) -> Path:
    sig = sign(manifests_dir, key)
    out_path = manifests_dir / SIG_FILENAME
    out_path.write_text(json.dumps(sig, indent=2, sort_keys=True), encoding="utf-8")
    return out_path


def verify(manifests_dir: Path, key: bytes | None = None) -> tuple[bool, list[str]]:
    """Return (ok, errors). If no key configured, returns (True, ['unconfigured'])."""
    key = key if key is not None else _key_bytes()
    sig_path = manifests_dir / SIG_FILENAME

    if key is None:
        return True, ["MANIFEST_SIGNING_KEY not set; skipping verification"]
    if not sig_path.exists():
        return False, [f"signature file missing: {sig_path}"]

    try:
        sig = json.loads(sig_path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"signature file unreadable: {e}"]

    stored_digests = sig.get("digests") or {}
    stored_mac = sig.get("hmac") or ""

    table = json.dumps(stored_digests, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected_mac = hmac.new(key, table, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(stored_mac, expected_mac):
        return False, ["HMAC mismatch — signature file tampered or wrong key"]

    actual = compute_digests(manifests_dir)
    errors: list[str] = []
    for rel, digest in stored_digests.items():
        if rel not in actual:
            errors.append(f"missing manifest: {rel}")
        elif actual[rel] != digest:
            errors.append(f"tampered manifest: {rel}")
    for rel in actual:
        if rel not in stored_digests:
            errors.append(f"unsigned manifest: {rel}")

    return (not errors), errors
