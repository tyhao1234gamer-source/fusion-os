"""WINEPREFIX / Proton compat-data management -- one isolated prefix per game.

Isolation per title is deliberate: a broken DLL override or winetricks verb in
one game can never contaminate another. Prefixes live under:
    <FUSION_HOME>/prefixes/<game_id>/

This module does not *require* Wine to be installed to compute paths and plans;
`ensure()` only touches the filesystem when asked, and `plan()` returns the
steps it would take so the CLI can show them under --dry-run.
"""

from __future__ import annotations

import os

from .db import default_root
from .models import GameProfile, RuntimeKind


def prefix_root() -> str:
    return os.path.join(default_root(), "prefixes")


def prefix_path(game_id: str) -> str:
    return os.path.join(prefix_root(), game_id)


def plan(profile: GameProfile, kind: RuntimeKind) -> list[str]:
    """Human-readable steps to initialise this prefix (no side effects)."""
    p = profile.prefix or prefix_path(profile.id)
    steps = [f"create directory {p}"]
    if kind is RuntimeKind.WINE:
        steps.append(f"WINEPREFIX={p} wineboot --init")
    else:
        steps.append(f"create {os.path.join(p, 'pfx')} via proton (first run)")
    for dll, mode in profile.dll_overrides.items():
        steps.append(f"register DLL override {dll}={mode}")
    if profile.graphics.dxvk_version:
        steps.append(f"install DXVK {profile.graphics.dxvk_version} into prefix")
    if profile.graphics.vkd3d_version:
        steps.append(f"install VKD3D-Proton {profile.graphics.vkd3d_version} into prefix")
    return steps


def ensure(profile: GameProfile) -> str:
    """Create the prefix directory tree. Returns the resolved prefix path.

    Wine/Proton initialisation itself is driven by `launch` on first run; here
    we only guarantee the directory exists so env vars point somewhere valid.
    """
    p = profile.prefix or prefix_path(profile.id)
    os.makedirs(p, exist_ok=True)
    return p
