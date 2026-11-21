"""The game library model for the Fusion Gaming Shell.

Collects entries from two sources and presents them uniformly:

* Fusion Compatibility Manager profiles (Windows titles) -- read straight from
  <FUSION_HOME>/profiles/*.json.
* Steam library -- parsed from appmanifest_*.acf files under steamapps.

Pure and dependency-free, so it is unit-testable against a fake FUSION_HOME and
a fake steamapps dir. Launching is delegated: a Windows title hands back the
`fusion-compat run <id> --real` command; a Steam title hands back
`steam steam://rungameid/<appid>`.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


@dataclass
class GameEntry:
    key: str                 # unique within the shell
    title: str
    source: str              # "windows" | "steam"
    launch_argv: list[str]
    status: str = "unknown"  # measured status, if known
    subtitle: str = ""

    def label(self) -> str:
        tag = {"windows": "[WIN]", "steam": "[STEAM]",
               "app": "[APP]"}.get(self.source, "")
        return f"{tag} {self.title}"


def _fusion_home(root: str | None) -> str:
    return root or os.environ.get("FUSION_HOME") or os.path.join(
        os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
        "fusion",
    )


def from_compat_profiles(root: str | None = None,
                         compat_bin: str = "fusion-compat") -> list[GameEntry]:
    home = _fusion_home(root)
    pdir = os.path.join(home, "profiles")
    out: list[GameEntry] = []
    if not os.path.isdir(pdir):
        return out
    for name in sorted(os.listdir(pdir)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(pdir, name), encoding="utf-8") as fh:
                p = json.load(fh)
        except (OSError, ValueError):
            continue
        out.append(GameEntry(
            key=f"win:{p['id']}",
            title=p.get("title", p["id"]),
            source="windows",
            launch_argv=[compat_bin, "run", p["id"], "--real"],
            status=p.get("measured_status", "unknown"),
            subtitle=p.get("d3d", ""),
        ))
    return out


def from_steam(steamapps_dir: str | None = None) -> list[GameEntry]:
    candidates = [steamapps_dir] if steamapps_dir else [
        os.path.expanduser("~/.steam/steam/steamapps"),
        os.path.expanduser("~/.local/share/Steam/steamapps"),
    ]
    out: list[GameEntry] = []
    for d in candidates:
        if not d or not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not (name.startswith("appmanifest_") and name.endswith(".acf")):
                continue
            try:
                text = open(os.path.join(d, name), encoding="utf-8",
                            errors="ignore").read()
            except OSError:
                continue
            appid = re.search(r'"appid"\s*"(\d+)"', text)
            title = re.search(r'"name"\s*"([^"]+)"', text)
            if not appid:
                continue
            out.append(GameEntry(
                key=f"steam:{appid.group(1)}",
                title=title.group(1) if title else f"app {appid.group(1)}",
                source="steam",
                launch_argv=["steam", f"steam://rungameid/{appid.group(1)}"],
            ))
        break
    return out


# Preinstalled apps shown as launchable tiles. A command of [] means "detect";
# `from_apps` keeps only the ones actually present.
_APPS = [
    ("Steam",   "steam",   ["steam", "-gamepadui"]),
    ("Discord", "discord", ["discord"]),
    ("Firefox", "firefox", ["firefox"]),
    # Epic/GOG via Heroic (flatpak) -- Epic has no native Linux client.
    ("Epic (Heroic)", "flatpak-heroic",
     ["flatpak", "run", "com.heroicgameslauncher.hgl"]),
]


def _which(binary: str) -> bool:
    import shutil
    return shutil.which(binary) is not None


def _flatpak_installed(app_id: str) -> bool:
    import subprocess
    try:
        out = subprocess.run(["flatpak", "info", app_id], capture_output=True,
                             timeout=5)
        return out.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def from_apps(check=None) -> list[GameEntry]:
    """Preinstalled apps that are actually present on the system."""
    check = check or _default_app_check
    out: list[GameEntry] = []
    for title, key, argv in _APPS:
        if not check(key, argv):
            continue
        out.append(GameEntry(key=f"app:{key}", title=title, source="app",
                             launch_argv=argv, subtitle="app"))
    return out


def _default_app_check(key: str, argv: list[str]) -> bool:
    if key == "flatpak-heroic":
        return _which("flatpak") and _flatpak_installed("com.heroicgameslauncher.hgl")
    return _which(argv[0])


def build_library(root: str | None = None,
                  steamapps_dir: str | None = None,
                  app_check=None) -> list[GameEntry]:
    games = from_compat_profiles(root) + from_steam(steamapps_dir)
    games.sort(key=lambda g: g.title.lower())
    # Apps go first so they're easy to reach; games follow alphabetically.
    return from_apps(app_check) + games
