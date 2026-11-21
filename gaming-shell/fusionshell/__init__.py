"""Fusion Gaming Shell (fusionshell).

A lightweight, controller-first game launcher for PS4 Fusion OS. Lists Windows
titles (via the Compatibility Manager) and Steam games, applies a performance
profile on launch (via the Performance Engine), and runs with a pure, testable
render core plus an evdev gamepad layer. No desktop environment, no heavy
toolkit -- just curses.
"""

__version__ = "0.1.0"
__all__ = ["library", "ui", "input"]
