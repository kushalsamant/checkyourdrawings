import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def prune_old_outputs(output_dir: Path, *, max_age_hours: int) -> int:
    """Delete comparison PNGs older than the configured retention window."""
    if max_age_hours <= 0:
        return 0

    cutoff_timestamp = time.time() - (max_age_hours * 3600)
    removed_count = 0

    for output_path in output_dir.glob("comparison-*.png"):
        try:
            if output_path.stat().st_mtime < cutoff_timestamp:
                output_path.unlink()
                removed_count += 1
        except OSError as exc:
            logger.warning("Failed to remove old output %s: %s", output_path, exc)

    if removed_count:
        logger.info("Removed %d expired comparison output(s).", removed_count)

    return removed_count
