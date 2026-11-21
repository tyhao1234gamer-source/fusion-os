"""Unit tests for the pure launch-command builder. Stdlib unittest only.

Run: python3 -m unittest discover -s tests  (from the package dir)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fusioncompat.launch import build, format_command  # noqa: E402
from fusioncompat.models import (  # noqa: E402
    D3DVersion, GameProfile, GraphicsConfig, Runtime, RuntimeKind,
)


def wine_rt():
    return Runtime(RuntimeKind.WINE, "wine-ge-8-26", "8.26",
                   "/opt/fusion/runtimes/wine/wine-ge-8-26",
                   "/opt/fusion/runtimes/wine/wine-ge-8-26/bin/wine64")


def proton_rt():
    return Runtime(RuntimeKind.PROTON, "proton-9.0", "9.0",
                   "/opt/fusion/runtimes/proton/proton-9.0",
                   "/opt/fusion/runtimes/proton/proton-9.0/proton")


class TestBuild(unittest.TestCase):
    def test_wine_basic(self):
        p = GameProfile(id="hk", title="Hollow Knight",
                        exe="/games/hk/hollow_knight.exe",
                        runtime="wine-ge-8-26", prefix="/pfx/hk",
                        d3d=D3DVersion.DX11,
                        graphics=GraphicsConfig(dxvk_version="2.3"))
        env, argv = build(p, wine_rt())
        self.assertEqual(env["WINEPREFIX"], "/pfx/hk")
        self.assertEqual(argv[0], wine_rt().launcher)
        self.assertEqual(argv[1], "/games/hk/hollow_knight.exe")
        # shader cache redirected
        self.assertIn("MESA_SHADER_CACHE_DIR", env)
        self.assertEqual(env["DXVK_STATE_CACHE"], "1")

    def test_dll_overrides(self):
        p = GameProfile(id="g", title="g", exe="/g/g.exe",
                        runtime="wine-ge-8-26", prefix="/pfx/g",
                        dll_overrides={"dinput8": "n,b", "d3d11": "n"})
        env, _ = build(p, wine_rt())
        self.assertIn("dinput8=n,b", env["WINEDLLOVERRIDES"])
        self.assertIn("d3d11=n", env["WINEDLLOVERRIDES"])

    def test_proton_wiring(self):
        p = GameProfile(id="pz", title="pz", exe="/g/pz.exe",
                        runtime="proton-9.0", prefix="/pfx/pz")
        env, argv = build(p, proton_rt())
        self.assertEqual(env["STEAM_COMPAT_DATA_PATH"], "/pfx/pz")
        self.assertEqual(argv[1], "run")

    def test_gamescope_wrap(self):
        p = GameProfile(id="g", title="g", exe="/g/g.exe",
                        runtime="wine-ge-8-26", prefix="/pfx/g",
                        gamescope="-W 1920 -H 1080 -f")
        _, argv = build(p, wine_rt())
        self.assertEqual(argv[0], "gamescope")
        self.assertIn("--", argv)

    def test_profile_env_wins(self):
        p = GameProfile(id="g", title="g", exe="/g/g.exe",
                        runtime="wine-ge-8-26", prefix="/pfx/g",
                        env={"WINEDEBUG": "+timestamp"})
        env, _ = build(p, wine_rt())
        self.assertEqual(env["WINEDEBUG"], "+timestamp")  # overrides the -all default

    def test_format_is_shell_safe(self):
        p = GameProfile(id="g", title="g", exe="/games/My Game/g.exe",
                        runtime="wine-ge-8-26", prefix="/pfx/g")
        env, argv = build(p, wine_rt())
        line = format_command(env, argv)
        self.assertIn("'/games/My Game/g.exe'", line)


if __name__ == "__main__":
    unittest.main()
