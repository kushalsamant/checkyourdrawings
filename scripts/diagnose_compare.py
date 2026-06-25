#!/usr/bin/env python3
"""Run the compare pipeline locally and print diagnostic metadata.

For all MVP revision pairs, use scripts/test_mvp_assets.py instead.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import OUTPUT_DIR
from backend.app.services.comparison_pipeline import run_comparison_pipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose a local drawing comparison run.")
    parser.add_argument("drawing_a", type=Path, help="Path to Drawing A PDF")
    parser.add_argument("drawing_b", type=Path, help="Path to Drawing B PDF")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable COMPARE_DEBUG intermediate frame export",
    )
    args = parser.parse_args()

    if args.debug:
        import os

        os.environ["COMPARE_DEBUG"] = "true"
        from backend.app import config as app_config

        app_config.COMPARE_DEBUG = True

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result = run_comparison_pipeline(
        args.drawing_a.resolve(),
        args.drawing_b.resolve(),
        args.drawing_a.name,
        args.drawing_b.name,
    )
    payload = result.model_dump(mode="json")
    print(json.dumps(payload["metadata"], indent=2))
    print()
    print(f"PNG: {payload['image_path']}")
    print(f"PDF: {payload['pdf_path']}")
    if args.debug:
        print(f"Debug frames: {OUTPUT_DIR / 'debug'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
