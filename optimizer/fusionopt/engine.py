"""The optimization engine: apply a profile, snapshot first, restore on demand.

Reversibility is the contract. `apply()`:
  1. expands every tunable path (globs -> concrete per-CPU/per-disk paths),
  2. reads and snapshots the current value of each,
  3. writes the profile value,
  4. persists the snapshot to <FUSION_HOME>/optstate.json.

`restore()` replays the most recent snapshot, returning every touched knob to
exactly what it was. Services stopped by a profile are restarted on restore.

The engine never measures or claims a performance gain -- that is the
Benchmark's job (benchmarks/), run against a baseline. This module only makes
the change, reproducibly and reversibly.
"""

from __future__ import annotations

import json
import os
import tempfile
import time

from .backend import Backend
from .profiles import Profile, resolve


def _state_path(root: str | None) -> str:
    base = root or os.environ.get("FUSION_HOME") or os.path.join(
        os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
        "fusion",
    )
    return os.path.join(base, "optstate.json")


def _atomic_write(path: str, data: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(data)
    os.replace(tmp, path)


class Engine:
    def __init__(self, backend: Backend, root: str | None = None) -> None:
        self.backend = backend
        self.state_path = _state_path(root)

    # -- plan / apply ----------------------------------------------------
    def plan(self, profile: Profile) -> list[dict]:
        """Return the concrete list of writes without performing them."""
        actions: list[dict] = []
        for t in profile.tunables:
            paths = self.backend.expand(t.path)
            if not paths:
                actions.append({"key": t.key, "path": t.path, "status": "absent"})
                continue
            for p in paths:
                cur = self.backend.read(p)
                actions.append({
                    "key": t.key, "path": p, "from": cur, "to": t.value,
                    "status": "absent" if cur is None else "change"
                    if cur != t.value else "noop",
                })
        for s in profile.services:
            actions.append({"key": "service", "action": s.action, "name": s.name})
        return actions

    def apply(self, profile: Profile) -> dict:
        snapshot: dict[str, str] = {}
        applied, skipped = 0, 0
        for t in profile.tunables:
            for p in self.backend.expand(t.path):
                cur = self.backend.read(p)
                if cur is None:
                    skipped += 1
                    continue
                snapshot.setdefault(p, cur)  # remember the ORIGINAL only
                if cur != t.value and self.backend.write(p, t.value):
                    applied += 1
        services_started = []
        for s in profile.services:
            # Record how to undo: stop <-> start.
            undo = "start" if s.action == "stop" else "stop"
            self.backend.service(s.action, s.name)
            services_started.append({"undo": undo, "name": s.name})
        record = {
            "ts": int(time.time()),
            "profile": profile.name,
            "snapshot": snapshot,
            "services": services_started,
            "game_cpuset": profile.game_cpuset,
        }
        _atomic_write(self.state_path, json.dumps(record, indent=2))
        return {"profile": profile.name, "applied": applied, "skipped": skipped,
                "reversible_knobs": len(snapshot)}

    # -- restore ---------------------------------------------------------
    def restore(self) -> dict:
        if not os.path.exists(self.state_path):
            return {"restored": 0, "note": "no saved state"}
        with open(self.state_path, encoding="utf-8") as fh:
            record = json.load(fh)
        restored = 0
        for path, value in record.get("snapshot", {}).items():
            if self.backend.write(path, value):
                restored += 1
        for svc in record.get("services", []):
            self.backend.service(svc["undo"], svc["name"])
        os.unlink(self.state_path)
        return {"restored": restored, "profile": record.get("profile")}

    # -- status ----------------------------------------------------------
    def active(self) -> dict | None:
        if not os.path.exists(self.state_path):
            return None
        with open(self.state_path, encoding="utf-8") as fh:
            return json.load(fh)


def profile_by_name(name: str) -> Profile:
    return resolve(name)
