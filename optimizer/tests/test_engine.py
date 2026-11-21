"""Tests for the Performance Engine: apply changes values, restore reverts them.

Run: python3 -m unittest discover -s tests
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fusionopt.backend import DryRunBackend  # noqa: E402
from fusionopt.engine import Engine  # noqa: E402
from fusionopt.profiles import resolve  # noqa: E402


def seeded_backend():
    seed = {}
    for i in range(8):
        seed[f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor"] = "schedutil"
    seed["/proc/sys/vm/swappiness"] = "60"
    seed["/sys/block/sda/queue/scheduler"] = "[mq-deadline] none"
    seed["/proc/sys/vm/dirty_ratio"] = "20"
    seed["/proc/sys/vm/dirty_background_ratio"] = "10"
    seed["/sys/kernel/mm/transparent_hugepage/enabled"] = "always [madvise] never"
    seed["/sys/block/sda/queue/nr_requests"] = "64"
    seed["/proc/sys/kernel/sched_migration_cost_ns"] = "500000"
    return DryRunBackend(seed)


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_apply_extreme_sets_performance_on_all_cpus(self):
        be = seeded_backend()
        eng = Engine(be, self.tmp)
        eng.apply(resolve("extreme"))
        govs = [be.read(f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor")
                for i in range(8)]
        self.assertTrue(all(g == "performance" for g in govs))
        self.assertEqual(be.read("/proc/sys/vm/swappiness"), "10")

    def test_restore_reverts_everything(self):
        be = seeded_backend()
        eng = Engine(be, self.tmp)
        eng.apply(resolve("extreme"))
        res = eng.restore()
        self.assertGreater(res["restored"], 0)
        # Back to the original seeded values.
        self.assertEqual(be.read("/proc/sys/vm/swappiness"), "60")
        self.assertEqual(
            be.read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
            "schedutil")

    def test_services_stopped_then_restarted(self):
        be = seeded_backend()
        eng = Engine(be, self.tmp)
        eng.apply(resolve("extreme"))
        self.assertIn(("stop", "bluetooth.service"), be.services)
        eng.restore()
        self.assertIn(("start", "bluetooth.service"), be.services)

    def test_competitive_pins_cluster(self):
        self.assertEqual(resolve("competitive").game_cpuset, "0-3")

    def test_absent_knob_is_skipped_not_crashed(self):
        be = DryRunBackend({"/proc/sys/vm/swappiness": "60"})  # minimal
        eng = Engine(be, self.tmp)
        res = eng.apply(resolve("balanced"))
        self.assertGreaterEqual(res["skipped"], 1)  # governor files absent
        self.assertEqual(be.read("/proc/sys/vm/swappiness"), "100")

    def test_alias_max_maps_to_extreme(self):
        self.assertEqual(resolve("max").name, "EXTREME PERFORMANCE")


if __name__ == "__main__":
    unittest.main()
