"""Benchmark records, baselines and comparisons.

The project rule (from the Phase 1 report): *no improvement is declared without
reproducible results against a reference*. This module enforces that shape:

* An IdleRecord captures RAM/CPU/boot at rest.
* A FrameRecord captures per-game frame data (avg FPS, 1% low, frametime).
* A Baseline is a named, stored record you compare future runs against.
* compare() reports deltas and never a verdict the numbers don't support.

Frame data is fed in from a frametime log (e.g. MangoHud's CSV, or any file of
millisecond frametimes). We compute the stats ourselves so the method is fixed
and reproducible.
"""

from __future__ import annotations

import json
import os
import statistics
import time


def fps_stats_from_frametimes(frametimes_ms: list[float]) -> dict:
    """avg FPS, 1% low FPS, and frametime percentiles from a frametime list."""
    ft = [f for f in frametimes_ms if f > 0]
    if not ft:
        return {"frames": 0}
    ft_sorted = sorted(ft)
    n = len(ft_sorted)
    # 1% low = mean FPS of the worst 1% of frames (the slowest = largest ft).
    worst_count = max(1, n // 100)
    worst = ft_sorted[-worst_count:]
    one_pct_low_fps = 1000.0 / (sum(worst) / len(worst))
    avg_fps = 1000.0 / (sum(ft) / n)
    return {
        "frames": n,
        "avg_fps": round(avg_fps, 1),
        "one_pct_low_fps": round(one_pct_low_fps, 1),
        "frametime_avg_ms": round(sum(ft) / n, 2),
        "frametime_p99_ms": round(ft_sorted[min(n - 1, int(n * 0.99))], 2),
        "frametime_max_ms": round(ft_sorted[-1], 2),
    }


def read_frametimes(path: str) -> list[float]:
    """Read frametimes (ms) from a file: one number per line, or MangoHud CSV."""
    out: list[float] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line[0].isalpha():
                continue  # header / comment
            token = line.split(",")[-1] if "," in line else line
            try:
                out.append(float(token))
            except ValueError:
                continue
    return out


class BaselineStore:
    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(
            os.environ.get("FUSION_HOME", os.path.expanduser("~/.local/share/fusion")),
            "baselines.json",
        )
        self._data: dict[str, dict] = {}
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (OSError, ValueError):
                self._data = {}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    def set(self, name: str, record: dict) -> None:
        record = dict(record)
        record["saved_ts"] = int(time.time())
        self._data[name] = record
        self.save()

    def get(self, name: str) -> dict | None:
        return self._data.get(name)

    def names(self) -> list[str]:
        return sorted(self._data)


def compare(baseline: dict, current: dict) -> dict:
    """Delta report between two records. Higher-is-better for FPS, lower for the rest."""
    out: dict[str, dict] = {}
    higher_better = {"avg_fps", "one_pct_low_fps", "cpu_count"}
    keys = set(baseline) | set(current)
    for k in sorted(keys):
        b, c = baseline.get(k), current.get(k)
        if not isinstance(b, (int, float)) or not isinstance(c, (int, float)):
            continue
        delta = round(c - b, 2)
        better = (delta > 0) if k in higher_better else (delta < 0)
        if delta == 0:
            better = None
        out[k] = {"baseline": b, "current": c, "delta": delta, "better": better}
    return out
