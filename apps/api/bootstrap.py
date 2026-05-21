"""
Manifest bootstrap: idempotent upsert of bundled manifests on startup.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from marketplace.core.models import AppCreate
from marketplace.storage.db import SessionLocal
from marketplace.storage.models import AppListing

logger = logging.getLogger(__name__)

MANIFESTS_DIR = Path(__file__).resolve().parent.parent.parent / "manifests"


def _rewrite_executor_url(url: str, api_base: str) -> str:
    if not url:
        return url
    for placeholder in ("http://127.0.0.1:8000", "http://localhost:8000"):
        if url.startswith(placeholder):
            return api_base + url[len(placeholder):]
    return url


def _verify_manifest_signature() -> None:
    """Verify bundled manifests if MANIFEST_SIGNING_KEY is set.

    Controlled by MANIFEST_VERIFY_MODE:
      - "warn" (default): log error but boot anyway. Sane during transition.
      - "strict": raise RuntimeError, refuse to boot on mismatch.
    """
    import os

    from marketplace.core.manifest_signing import verify

    ok, errors = verify(MANIFESTS_DIR)
    if ok:
        if errors:
            logger.info("Manifest signing: %s", errors[0])
        return

    mode = os.getenv("MANIFEST_VERIFY_MODE", "warn").lower()
    msg = "Manifest signature verification failed: " + "; ".join(errors)
    if mode == "strict":
        raise RuntimeError(msg)
    logger.error("%s (continuing because MANIFEST_VERIFY_MODE=warn)", msg)


def bootstrap_manifests() -> None:
    """Auto-register all manifests (idempotent upsert)."""
    if not MANIFESTS_DIR.exists():
        return

    _verify_manifest_signature()

    from marketplace.settings import API_BASE_URL
    api_base = API_BASE_URL.rstrip("/")

    db = SessionLocal()
    try:
        manifest_paths = list(MANIFESTS_DIR.glob("*.json")) + list(
            MANIFESTS_DIR.glob("categories/*/*.json")
        )

        for manifest_path in sorted(manifest_paths):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest = AppCreate.model_validate(manifest).model_dump()
                app_id = manifest.get("id")
                if not app_id:
                    continue
                row = db.get(AppListing, app_id)
                if row is None:
                    row = AppListing(id=app_id)
                    db.add(row)
                row.name = manifest.get("name", app_id)
                row.description = manifest.get("description", "")
                row.category = manifest.get("category", "general")
                row.subcategory = manifest.get("subcategory")
                row.tags = ",".join(manifest.get("tags", []))
                row.capabilities = ",".join(manifest.get("capabilities", []))
                row.freshness = manifest.get("freshness", "static")
                row.citations_supported = manifest.get("citations_supported", True)
                row.product_type = manifest.get("product_type", "api")
                row.latency_est_ms = manifest.get("latency_est_ms", 500)
                row.cost_est_usd = manifest.get("cost_est_usd", 0.0)
                row.executor_type = manifest.get("executor_type", "http_api")
                row.executor_url = _rewrite_executor_url(manifest.get("executor_url", ""), api_base)
                meta = dict(manifest.get("metadata", {}))
                meta["http_method"] = (manifest.get("http_method") or "GET").upper()
                if manifest.get("input_schema"):
                    meta["input_schema"] = manifest["input_schema"]
                row.extra_metadata = json.dumps(meta)
                db.commit()
            except Exception as e:
                logger.error("Error loading manifest %s: %s", manifest_path, e)
                continue
    finally:
        db.close()
