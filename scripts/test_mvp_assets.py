#!/usr/bin/env python3
"""Run all MVP revision PDF pairs and print a summary table."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.app.config import OUTPUT_DIR
from backend.app.services.comparison_pipeline import run_comparison_pipeline
from backend.tests.fixtures.mvp_assets import resolve_mvp_revision_pairs

MIN_GREEN_PIXELS = 100_000
MIN_TOTAL_INK_PIXELS = 500_000
MIN_GREEN_RATIO = 0.25
MAX_CHANGED_RATIO = 0.60
MIN_INLIER_RATIO = 0.55
MIN_OUTPUT_DPI = 200


def _format_row(columns: list[str], widths: list[int]) -> str:
    return "  ".join(column.ljust(width) for column, width in zip(columns, widths, strict=True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run MVP revision PDF compare checks.")
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

    pairs = resolve_mvp_revision_pairs(REPO_ROOT)
    if not pairs:
        print(
            "No MVP PDF pairs found. Commit fixtures under backend/tests/fixtures/pdfs/ "
            "or place originals in assets/.",
            file=sys.stderr,
        )
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    import gc

    headers = [
        "level",
        "green",
        "orange",
        "blue",
        "red",
        "green%",
        "changed%",
        "inlier",
        "dpi",
        "confidence",
        "status",
    ]
    widths = [7, 8, 8, 8, 8, 8, 9, 7, 5, 11, 8]
    print(_format_row(headers, widths))
    print(_format_row(["-" * width for width in widths], widths))

    failures = 0
    for level, drawing_a, drawing_b in pairs:
        try:
            result = run_comparison_pipeline(
                drawing_a,
                drawing_b,
                drawing_a.name,
                drawing_b.name,
            )
            overlay = result.metadata.overlay
            total_ink = (
                overlay.orange_pixels
                + overlay.blue_pixels
                + overlay.green_pixels
                + overlay.red_pixels
            )
            changed = overlay.orange_pixels + overlay.blue_pixels + overlay.red_pixels
            changed_ratio = changed / max(1, total_ink)
            green_ratio = overlay.green_pixels / max(1, total_ink)
            inlier_ratio = result.metadata.alignment.inlier_ratio
            dpi = result.metadata.output_page.raster_dpi
            confidence = result.metadata.alignment_confidence.status

            checks = [
                overlay.green_pixels >= MIN_GREEN_PIXELS,
                total_ink >= MIN_TOTAL_INK_PIXELS,
                green_ratio >= MIN_GREEN_RATIO,
                changed_ratio <= MAX_CHANGED_RATIO,
                inlier_ratio >= MIN_INLIER_RATIO,
                confidence == "high",
                dpi >= MIN_OUTPUT_DPI,
            ]
            status = "pass" if all(checks) else "fail"
            if status == "fail":
                failures += 1

            print(
                _format_row(
                    [
                        level,
                        str(overlay.green_pixels),
                        str(overlay.orange_pixels),
                        str(overlay.blue_pixels),
                        str(overlay.red_pixels),
                        f"{green_ratio * 100:.1f}",
                        f"{changed_ratio * 100:.1f}",
                        f"{inlier_ratio:.2f}",
                        str(dpi),
                        confidence,
                        status,
                    ],
                    widths,
                )
            )
        except Exception as exc:
            failures += 1
            print(
                _format_row(
                    [
                        level,
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "-",
                        "error",
                    ],
                    widths,
                )
            )
            print(f"  {type(exc).__name__}: {exc}", file=sys.stderr)
        finally:
            gc.collect()

    if args.debug:
        print(f"\nDebug frames: {OUTPUT_DIR / 'debug'}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
