import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("CYD_AUTH_REQUIRED", "false")

# Tests import `backend.app...`; ensure the repository root is importable in CI.
REPO_ROOT = Path(__file__).resolve().parents[2]
repo_root = str(REPO_ROOT)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)


@pytest.fixture(autouse=True)
def reset_compare_lock() -> None:
    from backend.app.routes import compare as compare_route

    if compare_route._compare_lock.locked():
        compare_route._compare_lock.release()
    yield
    if compare_route._compare_lock.locked():
        compare_route._compare_lock.release()
