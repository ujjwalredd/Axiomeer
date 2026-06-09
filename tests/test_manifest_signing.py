"""
Tests for manifest signing + verification.
"""
from __future__ import annotations

import json

from marketplace.core import manifest_signing as ms


def _setup_manifests(tmp_path, monkeypatch):
    d = tmp_path / "manifests"
    d.mkdir()
    (d / "cat").mkdir()
    (d / "cat").mkdir(exist_ok=True)
    (d / "a.json").write_text(json.dumps({"id": "a", "name": "A"}), encoding="utf-8")
    (d / "cat" / "b.json").mkdir if False else None
    (d / "cat" / "b.json").write_text(json.dumps({"id": "b", "name": "B"}), encoding="utf-8")
    return d


def test_round_trip(tmp_path):
    d = _setup_manifests(tmp_path, None)
    key = b"test-key-32-bytes-long-padding-padding"
    sig_path = ms.write_signature(d, key)
    assert sig_path.exists()

    ok, errors = ms.verify(d, key)
    assert ok, errors


def test_tampered_manifest_detected(tmp_path):
    d = _setup_manifests(tmp_path, None)
    key = b"k" * 32
    ms.write_signature(d, key)

    (d / "a.json").write_text(json.dumps({"id": "a", "name": "TAMPERED"}), encoding="utf-8")

    ok, errors = ms.verify(d, key)
    assert not ok
    assert any("tampered" in e for e in errors)


def test_added_manifest_detected(tmp_path):
    d = _setup_manifests(tmp_path, None)
    key = b"k" * 32
    ms.write_signature(d, key)

    (d / "c.json").write_text(json.dumps({"id": "c", "name": "C"}), encoding="utf-8")

    ok, errors = ms.verify(d, key)
    assert not ok
    assert any("unsigned" in e for e in errors)


def test_wrong_key_rejected(tmp_path):
    d = _setup_manifests(tmp_path, None)
    ms.write_signature(d, b"right-key")
    ok, errors = ms.verify(d, b"wrong-key")
    assert not ok
    assert any("HMAC mismatch" in e for e in errors)


def test_no_key_configured_skips(tmp_path):
    d = _setup_manifests(tmp_path, None)
    ok, errors = ms.verify(d, key=None)
    assert ok
    assert any("MANIFEST_SIGNING_KEY" in e for e in errors)


def test_missing_signature_file_fails(tmp_path):
    d = _setup_manifests(tmp_path, None)
    ok, errors = ms.verify(d, key=b"x" * 16)
    assert not ok
    assert any("signature file missing" in e for e in errors)
