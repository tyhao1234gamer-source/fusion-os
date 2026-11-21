"""fusion-bluetooth against a fake bluetoothctl that logs its calls."""
import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fusion-bluetooth")

FAKE = r'''#!/bin/sh
echo "$*" >> "$LOG"
case "$1" in
  show) [ "$HAS_ADAPTER" = 1 ] && echo "Controller 00:11:22:33:44:55 (public)" ;;
  devices) printf 'Device AA:BB:CC:DD:EE:01 Wireless Controller\nDevice AA:BB:CC:DD:EE:02 Xbox Wireless Controller\n' ;;
  pair) [ "$PAIR_FAILS" = 1 ] && exit 1 ;;
esac
exit 0
'''


def run(stdin, adapter=True, pair_fails=False):
    d = tempfile.mkdtemp()
    ctl = os.path.join(d, "btctl")
    with open(ctl, "w") as f:
        f.write(FAKE)
    os.chmod(ctl, 0o755)
    log = os.path.join(d, "log")
    env = {**os.environ, "FUSION_BT_CTL": ctl, "FUSION_BT_SCAN_SECONDS": "1", "LOG": log,
           "HAS_ADAPTER": "1" if adapter else "0", "PAIR_FAILS": "1" if pair_fails else "0"}
    r = subprocess.run(["sh", SCRIPT], input=stdin, env=env, capture_output=True, text=True)
    calls = open(log).read().splitlines() if os.path.exists(log) else []
    return r, calls


class Bluetooth(unittest.TestCase):
    def test_pairs_trusts_connects_chosen_device(self):
        r, calls = run("2\n\n")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Xbox Wireless Controller", r.stdout)
        for c in ("pair AA:BB:CC:DD:EE:02", "trust AA:BB:CC:DD:EE:02", "connect AA:BB:CC:DD:EE:02"):
            self.assertIn(c, calls)
        self.assertIn("--timeout 1 scan on", calls)

    def test_no_adapter(self):
        r, calls = run("\n", adapter=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("adaptador", r.stdout)
        self.assertNotIn("power on", calls)

    def test_cancel(self):
        r, calls = run("\n")
        self.assertEqual(r.returncode, 0)
        self.assertFalse(any(c.startswith("pair") for c in calls))

    def test_pair_failure_reported(self):
        r, calls = run("1\n\n", pair_fails=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("trust AA:BB:CC:DD:EE:01", calls)


if __name__ == "__main__":
    unittest.main()
