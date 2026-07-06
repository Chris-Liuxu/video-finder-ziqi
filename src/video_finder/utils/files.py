from __future__ import annotations

from pathlib import Path
from uuid import uuid4


def ensure_work_dir(base: Path | None = None) -> Path:
    root = base or Path(".video_finder_runs")
    path = root / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path
