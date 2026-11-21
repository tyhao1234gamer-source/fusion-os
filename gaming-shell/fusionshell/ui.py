"""Shell UI state + a pure renderer, with a curses front-end on top.

`ShellState` + `render_frame()` are pure: given a state they return the list of
text lines that make up the screen. The curses loop and the test suite both use
them, so the UI logic is testable without a terminal. The curses layer only
translates key/gamepad events into state transitions and paints the lines.

Navigation is controller-first (see input.py): D-pad up/down moves, A launches,
Y cycles the performance profile, B quits -- mapped to arrow keys / Enter / p /
q on a keyboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .library import GameEntry

PROFILES = ["EXTREME", "COMPETITIVE", "BALANCED", "LOW"]


@dataclass
class ShellState:
    games: list[GameEntry]
    cursor: int = 0
    profile_idx: int = 2            # BALANCED
    message: str = ""
    width: int = 60
    height: int = 20

    @property
    def profile(self) -> str:
        return PROFILES[self.profile_idx]

    def move(self, delta: int) -> None:
        if not self.games:
            return
        self.cursor = (self.cursor + delta) % len(self.games)

    def cycle_profile(self) -> None:
        self.profile_idx = (self.profile_idx + 1) % len(PROFILES)
        self.message = f"performance profile -> {self.profile}"

    def selected(self) -> GameEntry | None:
        return self.games[self.cursor] if self.games else None


def render_frame(state: ShellState) -> list[str]:
    w = state.width
    lines: list[str] = []
    title = "PS4 FUSION OS  ::  Gaming Shell"
    lines.append(title.center(w))
    lines.append("─" * w)
    if not state.games:
        lines.append("")
        lines.append("  No games found.".ljust(w))
        lines.append("  Add Windows titles with: fusion-compat add ...".ljust(w))
    else:
        # Viewport around the cursor.
        visible = state.height - 6
        start = max(0, min(state.cursor - visible // 2,
                           max(0, len(state.games) - visible)))
        for i in range(start, min(len(state.games), start + visible)):
            g = state.games[i]
            marker = "▶" if i == state.cursor else " "
            status = f"[{g.status}]" if g.status and g.status != "unknown" else ""
            row = f" {marker} {g.label()}  {status}"
            lines.append(row[:w].ljust(w))
    lines.append("─" * w)
    bar = f" Profile: {state.profile:11}   A:Launch  Y:Profile  B:Quit "
    lines.append(bar[:w].ljust(w))
    if state.message:
        lines.append((" " + state.message)[:w].ljust(w))
    return lines


# ----------------------------------------------------------------------
# Curses front-end (only imported/used when actually running a terminal).
# ----------------------------------------------------------------------
def run_curses(state: ShellState, launcher=None) -> None:  # pragma: no cover
    import curses

    def _main(stdscr):
        curses.curs_set(0)
        stdscr.nodelay(False)
        try:
            from . import input as gamepad
            pad = gamepad.open_first_gamepad()
        except Exception:
            pad = None

        while True:
            state.height, state.width = stdscr.getmaxyx()
            stdscr.erase()
            for y, line in enumerate(render_frame(state)):
                if y < state.height:
                    stdscr.addnstr(y, 0, line, max(0, state.width - 1))
            stdscr.refresh()

            ev = _read_event(stdscr, pad)
            if ev == "up":
                state.move(-1)
            elif ev == "down":
                state.move(1)
            elif ev == "profile":
                state.cycle_profile()
            elif ev == "launch":
                g = state.selected()
                if g and launcher:
                    state.message = f"launching {g.title}..."
                    stdscr.erase(); stdscr.refresh()
                    curses.endwin()
                    launcher(g, state.profile)
                    return
            elif ev == "quit":
                return

    curses.wrapper(_main)


def _read_event(stdscr, pad):  # pragma: no cover
    import curses

    if pad is not None:
        from . import input as gamepad
        ev = gamepad.poll(pad, timeout_ms=50)
        if ev:
            return ev
    stdscr.timeout(50)
    ch = stdscr.getch()
    mapping = {
        curses.KEY_UP: "up", ord("k"): "up",
        curses.KEY_DOWN: "down", ord("j"): "down",
        ord("\n"): "launch", curses.KEY_ENTER: "launch",
        ord("p"): "profile", ord("y"): "profile",
        ord("q"): "quit", 27: "quit",
    }
    return mapping.get(ch)
