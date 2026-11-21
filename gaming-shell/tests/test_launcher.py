"""Tests for the fusion-launch shell script, with fake cage/dbus-run-session."""
import os
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(HERE, "fusion-launch")


def run(args, keymap=None, extra_env=None, with_dbus=True, with_cage=True):
    tmp = tempfile.mkdtemp()
    fakebin = os.path.join(tmp, "bin")
    os.makedirs(fakebin)
    # Fakes print what they were asked to run, plus the env we care about.
    fake = ('#!/bin/sh\necho "$(basename "$0") $*"; '
            'echo "XKB=${XKB_DEFAULT_LAYOUT:-}"; echo "RT=${XDG_RUNTIME_DIR:-}"\n')
    names = (["cage"] if with_cage else []) + (["dbus-run-session"] if with_dbus else [])
    for name in names:
        p = os.path.join(fakebin, name)
        open(p, "w").write(fake)
        os.chmod(p, 0o755)
    vconsole = os.path.join(tmp, "vconsole.conf")
    if keymap is not None:
        open(vconsole, "w").write(f'KEYMAP={keymap}\n')
    env = {"PATH": fakebin + ":/usr/bin:/bin", "FUSION_VCONSOLE": vconsole,
           "XDG_RUNTIME_DIR": os.path.join(tmp, "rt")}
    env.update(extra_env or {})
    return subprocess.run(["sh", SCRIPT, *args], env=env, capture_output=True,
                          text=True).stdout


class TestLauncher(unittest.TestCase):
    def test_starts_cage_with_dbus_when_no_display(self):
        out = run(["flatpak", "run", "com.valvesoftware.Steam"], keymap="pt-latin1")
        self.assertIn("dbus-run-session -- cage -- flatpak run com.valvesoftware.Steam", out)

    def test_portuguese_console_keymap_becomes_xkb_pt(self):
        self.assertIn("XKB=pt", run(["true"], keymap="pt-latin1"))

    def test_brazilian_and_uk_keymaps(self):
        self.assertIn("XKB=br", run(["true"], keymap="br-abnt2"))
        self.assertIn("XKB=gb", run(["true"], keymap="uk"))

    def test_existing_display_runs_app_directly(self):
        out = run(["echo", "direct"], extra_env={"WAYLAND_DISPLAY": "wayland-0"})
        self.assertEqual(out.strip(), "direct")

    def test_without_cage_runs_app_directly(self):
        out = run(["echo", "nocage"], with_cage=False)
        self.assertEqual(out.strip(), "nocage")

    def test_without_dbus_runs_cage_alone(self):
        out = run(["flatpak", "run", "x"], with_dbus=False)
        self.assertIn("cage -- flatpak run x", out)
        self.assertNotIn("dbus-run-session", out)


if __name__ == "__main__":
    unittest.main()
