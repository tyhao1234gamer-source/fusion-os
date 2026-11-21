"""Backends for reading/writing system tunables.

Everything the optimizer does goes through a Backend, so the exact same engine
code runs:

* for real, on target, via SysfsBackend (writes to /sys, /proc, runs systemctl);
* safely anywhere, via DryRunBackend, which records intended actions and serves
  reads from an in-memory fake -- this is what the test suite and `--dry-run`
  use.

This indirection is what makes every optimization *inspectable before it runs*
and *fully reversible* (the engine snapshots reads, then writes; restore replays
the snapshot). Nothing here touches clocks, voltages or fan curves.
"""

from __future__ import annotations

import glob
import subprocess
from abc import ABC, abstractmethod


class Backend(ABC):
    @abstractmethod
    def read(self, path: str) -> str | None:
        """Return the trimmed contents of a sysfs/proc file, or None if absent."""

    @abstractmethod
    def write(self, path: str, value: str) -> bool:
        """Write value to a sysfs/proc file. Return True on success."""

    @abstractmethod
    def expand(self, pattern: str) -> list[str]:
        """Glob-expand a path pattern (e.g. all per-CPU governor files)."""

    @abstractmethod
    def service(self, action: str, name: str) -> bool:
        """Run a service action: 'stop' | 'start' | 'mask' | 'unmask'."""


class SysfsBackend(Backend):
    def read(self, path: str) -> str | None:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return None

    def write(self, path: str, value: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(value)
            return True
        except OSError:
            return False

    def expand(self, pattern: str) -> list[str]:
        return sorted(glob.glob(pattern))

    def service(self, action: str, name: str) -> bool:
        try:
            return subprocess.call(["systemctl", action, name]) == 0
        except OSError:
            return False


class DryRunBackend(Backend):
    """Records actions; serves reads from a seeded in-memory map."""

    def __init__(self, seed: dict[str, str] | None = None) -> None:
        self.state: dict[str, str] = dict(seed or {})
        self.writes: list[tuple[str, str]] = []
        self.services: list[tuple[str, str]] = []

    def read(self, path: str) -> str | None:
        return self.state.get(path)

    def write(self, path: str, value: str) -> bool:
        self.writes.append((path, value))
        self.state[path] = value  # so a later read reflects the intended write
        return True

    def expand(self, pattern: str) -> list[str]:
        if "*" not in pattern:
            return [pattern] if pattern in self.state else [pattern]
        import fnmatch

        hits = [k for k in self.state if fnmatch.fnmatch(k, pattern)]
        return sorted(hits) if hits else []

    def service(self, action: str, name: str) -> bool:
        self.services.append((action, name))
        return True
