"""Execution logging and compatibility reporting.

Every real run appends a record to <FUSION_HOME>/runs/<game_id>.jsonl. A run
record carries only *measured* facts (exit code, wall time, average FPS if the
benchmark overlay fed us one) -- never a guess. `summarise()` turns the log
into a measured CompatStatus, which is the ONLY thing allowed to set a
profile's `measured_status`.
"""

from __future__ import annotations

import json
import os
import time

from .db import default_root
from .models import CompatStatus


def _runs_path(game_id: str) -> str:
    return os.path.join(default_root(), "runs", f"{game_id}.jsonl")


def record_run(
    game_id: str,
    exit_code: int,
    seconds: float,
    avg_fps: float | None = None,
    note: str = "",
) -> None:
    path = _runs_path(game_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = {
        "ts": int(time.time()),
        "exit_code": exit_code,
        "seconds": round(seconds, 2),
        "avg_fps": avg_fps,
        "note": note,
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_runs(game_id: str) -> list[dict]:
    path = _runs_path(game_id)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def summarise(game_id: str) -> CompatStatus:
    """Derive a measured status from the run log. Conservative on purpose."""
    runs = load_runs(game_id)
    if not runs:
        return CompatStatus.UNKNOWN
    last = runs[-1]
    # A run shorter than ~20s that exits nonzero reads as a crash.
    if last["exit_code"] != 0 and last["seconds"] < 20:
        return CompatStatus.BROKEN
    fps = last.get("avg_fps")
    if fps is None:
        # Ran for a while, exited cleanly, but we have no frame data.
        return CompatStatus.RUNNABLE if last["seconds"] > 60 else CompatStatus.MENU_ONLY
    if fps >= 45:
        return CompatStatus.PLAYABLE
    if fps >= 25:
        return CompatStatus.RUNNABLE
    return CompatStatus.MENU_ONLY
