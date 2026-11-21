"""Tests for the setup wizard flow using a fake backend + scripted answers."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fusionsetup.backend import SetupBackend, WifiNetwork  # noqa: E402
from fusionsetup.wizard import run_wizard  # noqa: E402


class FakeBackend(SetupBackend):
    def __init__(self, ethernet=False, wifi=None, tzs=None):
        self.calls = []
        self._eth = ethernet
        self._wifi = wifi if wifi is not None else [
            WifiNetwork("HomeNet", 80, True), WifiNetwork("Cafe", 40, False)]
        self._tzs = tzs if tzs is not None else ["Europe/Lisbon", "UTC"]

    def list_timezones(self): return self._tzs
    def set_timezone(self, tz): self.calls.append(("tz", tz)); return True
    def list_keymaps(self): return ["pt-latin1", "us"]
    def set_keymap(self, km): self.calls.append(("km", km)); return True
    def set_locale(self, loc): self.calls.append(("locale", loc)); return True
    def has_ethernet_carrier(self): return self._eth
    def wifi_scan(self): return self._wifi
    def wifi_connect(self, ssid, psk):
        self.calls.append(("wifi", ssid, psk)); return True


def scripted(answers):
    """Return an ask() that pops answers in order; records prompts seen."""
    it = iter(answers)

    def ask(prompt, options=None, default=None, password=False):
        return next(it)
    return ask


class TestWizard(unittest.TestCase):
    def test_full_wifi_flow_no_account(self):
        be = FakeBackend(ethernet=False)
        ask = scripted(["pt_PT.UTF-8", "Europe/Lisbon", "pt-latin1",
                        "Wi-Fi", "HomeNet", "s3cret"])
        r = run_wizard(be, ask)
        self.assertEqual(r.locale, "pt_PT.UTF-8")
        self.assertEqual(r.timezone, "Europe/Lisbon")
        self.assertEqual(r.keymap, "pt-latin1")
        self.assertEqual(r.network, "wifi:HomeNet")
        self.assertIn(("wifi", "HomeNet", "s3cret"), be.calls)
        # No account/login was ever asked for or recorded.
        self.assertFalse(any(c[0] == "account" for c in be.calls))

    def test_ethernet_detected(self):
        be = FakeBackend(ethernet=True)
        ask = scripted(["en_US.UTF-8", "UTC", "us", "Ethernet"])
        r = run_wizard(be, ask)
        self.assertEqual(r.network, "ethernet")

    def test_open_wifi_no_password(self):
        be = FakeBackend(ethernet=False,
                         wifi=[WifiNetwork("FreeCafe", 70, False)])
        ask = scripted(["pt_PT.UTF-8", "Europe/Lisbon", "pt-latin1",
                        "Wi-Fi", "FreeCafe"])  # no password prompt consumed
        r = run_wizard(be, ask)
        self.assertEqual(r.network, "wifi:FreeCafe")
        self.assertIn(("wifi", "FreeCafe", None), be.calls)

    def test_invalid_timezone_warns_not_set(self):
        be = FakeBackend(tzs=["Europe/Lisbon"])
        ask = scripted(["pt_PT.UTF-8", "Mars/Olympus", "pt-latin1", "Saltar"])
        r = run_wizard(be, ask)
        self.assertEqual(r.timezone, "")               # not applied
        self.assertTrue(any("Mars/Olympus" in w for w in r.warnings))

    def test_skip_network(self):
        be = FakeBackend(ethernet=False)
        ask = scripted(["pt_PT.UTF-8", "UTC", "us", "Saltar"])
        r = run_wizard(be, ask)
        self.assertEqual(r.network, "skipped")


if __name__ == "__main__":
    unittest.main()
