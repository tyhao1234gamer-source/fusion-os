"""Build the exact environment and argv to launch a title.

This is the heart of the manager. `build()` is a *pure function*: given a
profile and its runtime, it returns (env, argv) without touching the system,
so it can be unit-tested and shown under --dry-run. `run()` is the only thing
that actually execs.

PS4-specific tuning baked into the environment
----------------------------------------------
* Shader caches are redirected to a persistent, per-title location and given
  generous size -- recompilation stutter is the worst offender on the Jaguar,
  and a warm cache is the single biggest real-world win.
* RADV is told to keep its pipeline cache; ACO is already the RADV default.
* Proton is pointed at a Fusion compat-data path and told not to phone Steam
  when run outside it.
Nothing here raises clocks, voltages or thermal limits -- out of scope by
design.
"""

from __future__ import annotations

import os
import shlex

from .db import default_root
from .models import GameProfile, Runtime, RuntimeKind


def _shader_cache_dir(game_id: str) -> str:
    return os.path.join(default_root(), "shadercache", game_id)


def build(profile: GameProfile, runtime: Runtime) -> tuple[dict[str, str], list[str]]:
    """Return (environment, argv). Pure -- no filesystem or process side effects."""
    env: dict[str, str] = {}
    prefix = profile.prefix or os.path.join(default_root(), "prefixes", profile.id)
    cache = _shader_cache_dir(profile.id)

    # --- Persistent shader caching (Mesa/radeonsi, RADV, DXVK) ---
    if profile.graphics.shader_cache:
        env["MESA_SHADER_CACHE_DISABLE"] = "false"
        env["MESA_SHADER_CACHE_DIR"] = cache
        env["MESA_SHADER_CACHE_MAX_SIZE"] = "2G"
        env["DXVK_STATE_CACHE"] = "1"
        env["DXVK_STATE_CACHE_PATH"] = cache
        env["__GL_SHADER_DISK_CACHE"] = "1"
        env["RADV_PIPELINE_CACHE"] = "1"

    # --- DXVK / VKD3D knobs ---
    if profile.graphics.dxvk_hud:
        env["DXVK_HUD"] = profile.graphics.dxvk_hud
    if profile.graphics.dxvk_async:
        # Only honoured by async-capable builds; harmless otherwise.
        env["DXVK_ASYNC"] = "1"

    # --- DLL overrides ---
    if profile.dll_overrides:
        env["WINEDLLOVERRIDES"] = ";".join(
            f"{dll}={mode}" for dll, mode in profile.dll_overrides.items()
        )

    # --- Runtime-specific wiring ---
    if runtime.kind is RuntimeKind.WINE:
        env["WINEPREFIX"] = prefix
        env.setdefault("WINEDEBUG", "-all")  # silence logs -> less CPU/IO
        argv = [runtime.launcher, profile.exe, *profile.args]
    else:  # Proton
        env["STEAM_COMPAT_DATA_PATH"] = prefix
        # Allow running a bare exe through Proton outside a Steam session.
        env.setdefault(
            "STEAM_COMPAT_CLIENT_INSTALL_PATH",
            os.path.expanduser("~/.steam/steam"),
        )
        env["PROTON_NO_ESYNC"] = env.get("PROTON_NO_ESYNC", "0")
        argv = [runtime.launcher, "run", profile.exe, *profile.args]

    # --- Profile-supplied env wins last (explicit user overrides) ---
    env.update(profile.env)

    # --- Optional gamescope wrapper ---
    if profile.gamescope:
        argv = ["gamescope", *shlex.split(profile.gamescope), "--", *argv]

    return env, argv


def format_command(env: dict[str, str], argv: list[str]) -> str:
    """Render an env+argv as a copy-pasteable shell line."""
    parts = [f"{k}={shlex.quote(v)}" for k, v in sorted(env.items())]
    parts.extend(shlex.quote(a) for a in argv)
    return " ".join(parts)


def run(profile: GameProfile, runtime: Runtime, dry_run: bool = True) -> int:
    """Execute (or, under dry_run, print) the launch command.

    Returns the child exit code, or 0 for a dry run.
    """
    from . import prefix as prefix_mod

    env, argv = build(profile, runtime)
    if dry_run:
        print(format_command(env, argv))
        return 0

    prefix_mod.ensure(profile)
    os.makedirs(_shader_cache_dir(profile.id), exist_ok=True)
    full_env = dict(os.environ)
    full_env.update(env)
    import subprocess

    return subprocess.call(argv, env=full_env)
