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


class TestApps(unittest.TestCase):
    def _apps(self, native=(), flatpaks=(), launcher=True):
        from fusionshell.library import from_apps
        return from_apps(which=lambda b: b in native,
                         flatpak_has=lambda i: i in flatpaks,
                         launcher_present=launcher)

    def test_flatpak_apps_resolve_through_launcher(self):
        apps = self._apps(flatpaks={"com.valvesoftware.Steam", "org.mozilla.firefox"})
        self.assertEqual([a.title for a in apps], ["Steam", "Firefox"])
        self.assertEqual(apps[0].launch_argv,
                         ["fusion-launch", "flatpak", "run",
                          "com.valvesoftware.Steam", "-gamepadui"])

    def test_native_wins_over_flatpak(self):
        apps = self._apps(native={"discord"}, flatpaks={"com.discordapp.Discord"})
        self.assertEqual(apps[0].launch_argv, ["fusion-launch", "discord"])

    def test_steam_is_listed_first(self):
        apps = self._apps(flatpaks={"org.mozilla.firefox",
                                    "com.heroicgameslauncher.hgl",
                                    "com.valvesoftware.Steam"})
        self.assertEqual(apps[0].title, "Steam")

    def test_no_launcher_runs_app_directly(self):
        apps = self._apps(native={"firefox"}, launcher=False)
        self.assertEqual(apps[0].launch_argv, ["firefox"])

    def test_nothing_installed(self):
        self.assertEqual(self._apps(), [])

    def test_app_label_tag(self):
        apps = self._apps(native={"discord"})
        self.assertIn("[APP] Discord", apps[0].label())


class TestProfileCommand(unittest.TestCase):
    def test_unprivileged_uses_scoped_sudo(self):
        from fusionshell.cli import profile_command
        self.assertEqual(profile_command("EXTREME", euid=1000),
                         ["sudo", "-n", "/usr/bin/fusion-opt", "apply",
                          "extreme", "--real"])

    def test_root_runs_directly(self):
        from fusionshell.cli import profile_command
        self.assertEqual(profile_command("LOW", euid=0)[0], "/usr/bin/fusion-opt")


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




class TestSystemTools(unittest.TestCase):
    def test_tools_only_when_present(self):
        from fusionshell.library import from_system
        none = from_system(which=lambda b: False)
        self.assertEqual(none, [])
        both = from_system(which=lambda b: True)
        self.assertEqual([g.key for g in both], ["sys:bluetooth", "sys:install"])
        self.assertEqual(both[1].launch_argv, ["sudo", "fusion-install-disk"])
        self.assertTrue(both[0].label().startswith("[SYS]"))

    def test_system_tool_skips_game_profile(self):
        from unittest import mock
        from fusionshell import cli
        g = GameEntry(key="sys:x", title="x", source="system", launch_argv=["true"])
        with mock.patch.object(cli, "_apply_profile") as ap, \
             mock.patch.object(cli.subprocess, "call", return_value=0):
            cli.launch_game(g, "balanced")
        ap.assert_not_called()


if __name__ == "__main__":
    unittest.main()
