#!/usr/bin/env python3
"""
Validate all API manifests against schema.
Run from project root: python scripts/validate_manifests.py
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from marketplace.core.models import AppCreate


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    manifests_dir = project_root / "manifests"
    if not manifests_dir.exists():
        print(f"Manifests dir not found: {manifests_dir}")
        return 1

    manifest_paths = list(manifests_dir.glob("*.json")) + list(
        manifests_dir.glob("categories/*/*.json")
    )

    errors = []
    for manifest_path in sorted(manifest_paths):
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = AppCreate.model_validate(raw)
            if not manifest.executor_url:
                errors.append(f"{manifest_path.name}: missing executor_url")
        except Exception as e:
            errors.append(f"{manifest_path.name}: validation failed - {e}")

    if errors:
        print("Manifest validation FAILED:\n")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"OK: Validated {len(manifest_paths)} manifests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
