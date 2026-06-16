import sys
from pathlib import Path

# Tests import `backend.app...`; ensure the repository root is importable in CI.
REPO_ROOT = Path(__file__).resolve().parents[2]
repo_root = str(REPO_ROOT)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
