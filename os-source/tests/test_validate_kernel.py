import os
import subprocess
import sys
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "validate-kernel-config.py")


def w(d, name, text):
    p = os.path.join(d, name)
    with open(p, "w") as f:
        f.write(text)
    return p


class ValidateKernel(unittest.TestCase):
    def test_ok_and_module_satisfied_by_builtin(self):
        d = tempfile.mkdtemp()
        cfg = w(d, ".config", "CONFIG_A=y\nCONFIG_B=y\n# CONFIG_C is not set\n")
        frag = w(d, "f", "CONFIG_A=y\nCONFIG_B=m\n# CONFIG_C is not set\n")
        r = subprocess.run([sys.executable, TOOL, cfg, frag], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_reports_dropped(self):
        d = tempfile.mkdtemp()
        cfg = w(d, ".config", "CONFIG_A=m\n")
        f1 = w(d, "f1", "CONFIG_A=y\nCONFIG_D=m\n")
        r = subprocess.run([sys.executable, TOOL, cfg, f1], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("CONFIG_A: wanted y, got m", r.stdout)
        self.assertIn("CONFIG_D: wanted m, got n", r.stdout)

    def test_later_fragment_wins(self):
        d = tempfile.mkdtemp()
        cfg = w(d, ".config", "CONFIG_A=m\n")
        f1 = w(d, "f1", "CONFIG_A=y\n")
        f2 = w(d, "f2", "CONFIG_A=m\n")
        r = subprocess.run([sys.executable, TOOL, cfg, f1, f2], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
