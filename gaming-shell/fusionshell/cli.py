"""CLI / entry logic for the Fusion Gaming Shell.

    fusion-shell                 launch the TUI
    fusion-shell --list          print the library (no TUI; scriptable/testable)
    fusion-shell --render        print one rendered frame (debug/testing)

On launch of a game the shell asks the Performance Engine to apply the selected
profile, then execs the game. Both steps are shown; nothing hidden.
"""

from __future__ import annotations

import argparse
import os
import subprocess

from .library import GameEntry, build_library
from .ui import ShellState, render_frame


def _apply_profile(profile: str, opt_bin: str = "fusion-opt") -> None:
    # Map shell label to the engine's profile key; apply for real.
    key = profile.lower()
    try:
        subprocess.call([opt_bin, "apply", key, "--real"])
    except OSError:
        print(f"(could not run {opt_bin}; skipping profile apply)")


def launch_game(game: GameEntry, profile: str) -> int:
    print(f"profile: {profile}")
    _apply_profile(profile)
    print("launch:", " ".join(game.launch_argv))
    try:
        return subprocess.call(game.launch_argv)
    except OSError as e:
        print(f"launch failed: {e}")
        return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="fusion-shell", description="Fusion Gaming Shell")
    p.add_argument("--root", help="FUSION_HOME override")
    p.add_argument("--steamapps", help="steamapps dir override")
    p.add_argument("--list", action="store_true", help="print library and exit")
    p.add_argument("--render", action="store_true", help="print one frame and exit")
    args = p.parse_args(argv)

    games = build_library(args.root, args.steamapps)

    if args.list:
        if not games:
            print("no games found")
        for g in games:
            print(f"{g.label():40} {g.status:10} {' '.join(g.launch_argv)}")
        return 0

    state = ShellState(games=games)
    if args.render:
        print("\n".join(render_frame(state)))
        return 0

    if not os.isatty(0):
        print("fusion-shell needs a terminal; use --list or --render otherwise.")
        return 1

    from .ui import run_curses
    run_curses(state, launcher=launch_game)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
