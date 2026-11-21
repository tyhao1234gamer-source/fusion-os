"""Tests for FPS statistics and baseline comparison."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fusionbench.record import (  # noqa: E402
    BaselineStore, compare, fps_stats_from_frametimes,
)


class TestStats(unittest.TestCase):
    def test_steady_60fps(self):
        # 1000 frames at exactly 16.667 ms => 60 fps, 1% low also ~60.
        ft = [16.667] * 1000
        s = fps_stats_from_frametimes(ft)
        self.assertAlmostEqual(s["avg_fps"], 60.0, delta=0.2)
        self.assertAlmostEqual(s["one_pct_low_fps"], 60.0, delta=0.2)

    def test_one_pct_low_catches_spikes(self):
        ft = [16.667] * 990 + [100.0] * 10   # ten big stutters
        s = fps_stats_from_frametimes(ft)
        self.assertLess(s["one_pct_low_fps"], s["avg_fps"])  # 1% low is worse
        self.assertEqual(s["frames"], 1000)

    def test_empty_is_safe(self):
        self.assertEqual(fps_stats_from_frametimes([])["frames"], 0)

    def test_compare_flags_direction(self):
        base = {"avg_fps": 30.0, "frametime_avg_ms": 33.0}
        cur = {"avg_fps": 42.0, "frametime_avg_ms": 24.0}
        rep = compare(base, cur)
        self.assertTrue(rep["avg_fps"]["better"])          # more fps = better
        self.assertTrue(rep["frametime_avg_ms"]["better"])  # less ms = better

    def test_baseline_roundtrip(self):
        tmp = os.path.join(tempfile.mkdtemp(), "b.json")
        st = BaselineStore(tmp)
        st.set("stock", {"avg_fps": 28.0})
        self.assertEqual(BaselineStore(tmp).get("stock")["avg_fps"], 28.0)


if __name__ == "__main__":
    unittest.main()
