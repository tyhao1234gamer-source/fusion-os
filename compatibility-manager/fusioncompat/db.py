"""JSON-backed stores for profiles and the compatibility database.

Two stores, both plain directories of JSON so they are diff-friendly and can
live in git:

* ProfileStore  -- one file per game profile under <root>/profiles/<id>.json
* CompatDB      -- a single curated file of known-title results that ships with
                   Fusion OS and is updated from real benchmark runs.

Writes are atomic (temp file + os.replace) so a crash never leaves a
half-written profile.
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Iterator

from .models import CompatStatus, GameProfile


def _atomic_write(path: str, data: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def default_root() -> str:
    base = os.environ.get("FUSION_HOME") or os.path.join(
        os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
        "fusion",
    )
    return base


class ProfileStore:
    def __init__(self, root: str | None = None) -> None:
        self.root = root or default_root()
        self.dir = os.path.join(self.root, "profiles")

    def path_for(self, game_id: str) -> str:
        return os.path.join(self.dir, f"{game_id}.json")

    def save(self, profile: GameProfile) -> None:
        _atomic_write(
            self.path_for(profile.id),
            json.dumps(profile.to_json(), indent=2, ensure_ascii=False),
        )

    def load(self, game_id: str) -> GameProfile:
        with open(self.path_for(game_id), encoding="utf-8") as fh:
            return GameProfile.from_json(json.load(fh))

    def exists(self, game_id: str) -> bool:
        return os.path.exists(self.path_for(game_id))

    def delete(self, game_id: str) -> None:
        p = self.path_for(game_id)
        if os.path.exists(p):
            os.unlink(p)

    def all(self) -> Iterator[GameProfile]:
        if not os.path.isdir(self.dir):
            return
        for name in sorted(os.listdir(self.dir)):
            if name.endswith(".json"):
                try:
                    with open(os.path.join(self.dir, name), encoding="utf-8") as fh:
                        yield GameProfile.from_json(json.load(fh))
                except (OSError, ValueError):
                    continue


class CompatDB:
    """Curated known-good-settings database, keyed by lowercase title."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.path.join(default_root(), "compatdb.json")
        self._data: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as fh:
                    self._data = json.load(fh)
            except (OSError, ValueError):
                self._data = {}

    def save(self) -> None:
        _atomic_write(self.path, json.dumps(self._data, indent=2, ensure_ascii=False))

    @staticmethod
    def _key(title: str) -> str:
        return title.strip().lower()

    def get(self, title: str) -> dict | None:
        return self._data.get(self._key(title))

    def record(self, title: str, status: CompatStatus, settings: dict) -> None:
        self._data[self._key(title)] = {
            "title": title,
            "status": status.value,
            "settings": settings,
        }
        self.save()

    def titles(self) -> list[str]:
        return [v.get("title", k) for k, v in sorted(self._data.items())]
