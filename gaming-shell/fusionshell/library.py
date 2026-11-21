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


# Bundled apps shown as launchable tiles, Steam first. Each app can come as a
# native package (Arch edition) or from Flathub (from-source edition); the
# first one present wins. Everything is launched through `fusion-launch`,
# which starts the fullscreen compositor when no display is running yet.
@dataclass(frozen=True)
class App:
    title: str
    key: str
    native: tuple                 # argv when installed natively
    flatpak_id: str               # Flathub ID
    flatpak_args: tuple = ()


APPS = (
    App("Steam", "steam", ("steam", "-gamepadui"),
        "com.valvesoftware.Steam", ("-gamepadui",)),
    App("Discord", "discord", ("discord",), "com.discordapp.Discord"),
    # Epic has no native Linux client: Heroic is the standard way to run it.
    App("Epic (Heroic)", "heroic", ("heroic",), "com.heroicgameslauncher.hgl"),
    App("Firefox", "firefox", ("firefox",), "org.mozilla.firefox"),
)

LAUNCHER = "fusion-launch"


def _which(binary: str) -> bool:
    import shutil
    return shutil.which(binary) is not None


def _flatpak_installed(app_id: str) -> bool:
    import subprocess
    if not _which("flatpak"):
        return False
    try:
        out = subprocess.run(["flatpak", "info", app_id], capture_output=True,
                             timeout=5)
        return out.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def resolve_app(app: App, which=_which, flatpak_has=_flatpak_installed,
                launcher_present=None) -> list[str] | None:
    """Return the argv to launch `app`, or None if it is not installed."""
    if which(app.native[0]):
        argv = list(app.native)
    elif flatpak_has(app.flatpak_id):
        argv = ["flatpak", "run", app.flatpak_id, *app.flatpak_args]
    else:
        return None
    present = which(LAUNCHER) if launcher_present is None else launcher_present
    return [LAUNCHER, *argv] if present else argv


def from_apps(which=_which, flatpak_has=_flatpak_installed,
              launcher_present=None) -> list[GameEntry]:
    """Bundled apps that are actually installed, in menu order."""
    out: list[GameEntry] = []
    for app in APPS:
        argv = resolve_app(app, which, flatpak_has, launcher_present)
        if argv is None:
            continue
        out.append(GameEntry(key=f"app:{app.key}", title=app.title,
                             source="app", launch_argv=argv, subtitle="app"))
    return out


def build_library(root: str | None = None,
                  steamapps_dir: str | None = None) -> list[GameEntry]:
    games = from_compat_profiles(root) + from_steam(steamapps_dir)
    games.sort(key=lambda g: g.title.lower())
    # Apps go first so they're easy to reach; games follow alphabetically.
    return from_apps() + games
