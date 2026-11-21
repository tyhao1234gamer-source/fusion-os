"""The tools installed into the image actually run (regression for the stale
fusion-detect wrapper found by the first QEMU boot)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


class InstalledTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp()
        subprocess.run([os.path.join(REPO, "scripts", "install-fusion-userspace.sh"), cls.root],
                       check=True, capture_output=True)
        cls.env = {**os.environ, "FUSION_LIB": os.path.join(cls.root, "usr/lib/fusion")}

    def tool(self, name, *args):
        return subprocess.run([sys.executable, os.path.join(self.root, "usr/bin", name), *args],
                              env=self.env, capture_output=True, text=True)

    def test_fusion_detect_json_as_firstboot_uses_it(self):
        r = self.tool("fusion-detect", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertIn("zram_mb", d["tuning"])
        self.assertIn("io_scheduler", d["tuning"])
        self.assertIn("nvidia_proprietary", d["drivers"])

    def test_fusion_detect_human_report(self):
        r = self.tool("fusion-detect")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Fusion machine report", r.stdout)

    def test_firstboot_calls_supported_options(self):
        fb = open(os.path.join(self.root, "usr/bin/fusion-firstboot")).read()
        self.assertIn("fusion-detect --json", fb)   # and --json is supported (above)

    def test_bash_scripts_need_bash_in_image(self):
        defconfig = open(os.path.join(REPO, "os-source/br-external/configs/fusion_x86_64_defconfig")).read()
        for name in ("fusion-firstboot", "fusion-perf-baseline", "fusion-game", "fusion-gpu"):
            first = open(os.path.join(self.root, "usr/bin", name)).readline()
            if "bash" in first:
                self.assertIn("BR2_PACKAGE_BASH=y", defconfig, name)


if __name__ == "__main__":
    unittest.main()
