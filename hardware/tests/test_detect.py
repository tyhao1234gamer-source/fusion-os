"""Tests for southbridge/GPU classification."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fusionhw.detect import classify  # noqa: E402


class TestClassify(unittest.TestCase):
    def test_aeolia_base_ps4(self):
        rec = classify([("104d", "908f"), ("1002", "9920")])
        self.assertEqual(rec.southbridge, "Aeolia")
        self.assertIn("Liverpool", rec.gpu)
        self.assertTrue(rec.internal_hdd)
        self.assertEqual(rec.mesa_pin, "latest")

    def test_baikal_caps_mesa_and_blocks_internal(self):
        rec = classify([("104d", "90c0"), ("1002", "98f0")])
        self.assertEqual(rec.southbridge, "Baikal")
        self.assertIn("Neo", rec.gpu)
        self.assertFalse(rec.internal_hdd)
        self.assertEqual(rec.mesa_pin, "<=25.1")

    def test_unknown_southbridge_is_honest(self):
        rec = classify([("8086", "1234")])  # not a PS4
        self.assertEqual(rec.southbridge, "UNKNOWN")
        self.assertEqual(rec.kernel, "UNKNOWN")
        self.assertFalse(rec.internal_hdd)


if __name__ == "__main__":
    unittest.main()
