"""System metric readers. Stdlib only; all read real /proc and /sys.

These are the measurements that back every performance claim in Fusion OS.
Nothing here is estimated -- if a source is unavailable the reader returns None
and the caller records "unavailable" rather than inventing a number.
"""

from __future__ import annotations

import os
import time


def mem_used_mb() -> float | None:
    """Used RAM in MiB, computed as MemTotal - MemAvailable (the honest figure)."""
    try:
        total = avail = None
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    total = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    avail = int(line.split()[1])
        if total is None or avail is None:
            return None
        return round((total - avail) / 1024.0, 1)
    except (OSError, ValueError):
        return None


def _cpu_times() -> tuple[int, int] | None:
    """Return (idle, total) jiffies from /proc/stat's aggregate line."""
    try:
        with open("/proc/stat", encoding="utf-8") as fh:
            parts = fh.readline().split()
        if parts[0] != "cpu":
            return None
        nums = [int(x) for x in parts[1:]]
        idle = nums[3] + (nums[4] if len(nums) > 4 else 0)  # idle + iowait
        return idle, sum(nums)
    except (OSError, ValueError, IndexError):
        return None


def cpu_busy_pct(sample_seconds: float = 1.0) -> float | None:
    """Average CPU busy % over a short sample window."""
    a = _cpu_times()
    if a is None:
        return None
    time.sleep(sample_seconds)
    b = _cpu_times()
    if b is None:
        return None
    idle_delta = b[0] - a[0]
    total_delta = b[1] - a[1]
    if total_delta <= 0:
        return None
    return round(100.0 * (1.0 - idle_delta / total_delta), 1)


def uptime_seconds() -> float | None:
    try:
        with open("/proc/uptime", encoding="utf-8") as fh:
            return float(fh.readline().split()[0])
    except (OSError, ValueError):
        return None


def cpu_count() -> int:
    return os.cpu_count() or 0


def boot_seconds() -> float | None:
    """Boot time via systemd-analyze if present; else None (don't guess)."""
    import shutil
    import subprocess

    if not shutil.which("systemd-analyze"):
        return None
    try:
        out = subprocess.check_output(["systemd-analyze", "time"], text=True,
                                      stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    # "Startup finished in ... = 12.345s"
    import re

    m = re.search(r"=\s*([\d.]+)s", out)
    return float(m.group(1)) if m else None


def snapshot(sample_seconds: float = 1.0) -> dict:
    """A full idle-state snapshot."""
    return {
        "mem_used_mb": mem_used_mb(),
        "cpu_busy_pct": cpu_busy_pct(sample_seconds),
        "cpu_count": cpu_count(),
        "uptime_s": uptime_seconds(),
        "boot_s": boot_seconds(),
    }
