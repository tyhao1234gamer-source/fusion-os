"""Tests for the library model, pure renderer, and gamepad decoding."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fusionshell import input as gamepad  # noqa: E402
from fusionshell.library import GameEntry  # noqa: E402
from fusionshell.ui import ShellState, render_frame  # noqa: E402


def demo_games():
    return [
        GameEntry("win:hk", "Hollow Knight", "windows",
                  ["fusion-compat", "run", "hk", "--real"], status="playable"),
        GameEntry("steam:400", "Portal", "steam",
                  ["steam", "steam://rungameid/400"]),
    ]


class TestUI(unittest.TestCase):
    def test_cursor_wraps(self):
        s = ShellState(games=demo_games())
        self.assertEqual(s.cursor, 0)
        s.move(-1)
        self.assertEqual(s.cursor, 1)  # wrapped to last
        s.move(1)
        self.assertEqual(s.cursor, 0)

    def test_profile_cycles(self):
        s = ShellState(games=demo_games())
        self.assertEqual(s.profile, "BALANCED")
        s.cycle_profile()
        self.assertEqual(s.profile, "LOW")

    def test_render_marks_selection_and_status(self):
        s = ShellState(games=demo_games())
        frame = "\n".join(render_frame(s))
        self.assertIn("▶", frame)
        self.assertIn("Hollow Knight", frame)
        self.assertIn("[playable]", frame)
        self.assertIn("Profile: BALANCED", frame)

    def test_render_empty_library(self):
        frame = "\n".join(render_frame(ShellState(games=[])))
        self.assertIn("No games found", frame)

    def test_selected_entry(self):
        s = ShellState(games=demo_games())
        self.assertEqual(s.selected().title, "Hollow Knight")


class TestGamepad(unittest.TestCase):
    def _ev(self, etype, code, value):
        return struct.pack(gamepad._EV_FORMAT, 0, 0, etype, code, value)

    def test_south_button_launches(self):
        data = self._ev(gamepad.EV_KEY, gamepad.BTN_SOUTH, 1)
        self.assertEqual(gamepad.decode(data), "launch")

    def test_dpad_down(self):
        data = self._ev(gamepad.EV_ABS, gamepad.ABS_HAT0Y, 1)
        self.assertEqual(gamepad.decode(data), "down")

    def test_keyup_ignored(self):
        data = self._ev(gamepad.EV_KEY, gamepad.BTN_SOUTH, 0)  # release
        self.assertIsNone(gamepad.decode(data))


if __name__ == "__main__":
    unittest.main()
