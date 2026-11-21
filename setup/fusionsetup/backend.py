"""System backend for the first-run setup wizard.

All side effects (timedatectl / localectl / nmcli) go through a backend, so the
wizard flow is fully testable with FakeBackend and never needs root or network
in tests. SystemBackend drives the real tools on target.

The wizard sets up region, timezone, keyboard and network ONLY. It deliberately
creates NO user account and asks for NO online sign-in -- Fusion auto-logs in a
local session user with no password prompt and no cloud account.
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class WifiNetwork:
    ssid: str
    signal: int           # 0-100
    secured: bool


class SetupBackend(ABC):
    @abstractmethod
    def list_timezones(self) -> list[str]: ...
    @abstractmethod
    def set_timezone(self, tz: str) -> bool: ...
    @abstractmethod
    def list_keymaps(self) -> list[str]: ...
    @abstractmethod
    def set_keymap(self, km: str) -> bool: ...
    @abstractmethod
    def set_locale(self, locale: str) -> bool: ...
    @abstractmethod
    def has_ethernet_carrier(self) -> bool: ...
    @abstractmethod
    def wifi_scan(self) -> list[WifiNetwork]: ...
    @abstractmethod
    def wifi_connect(self, ssid: str, psk: str | None) -> bool: ...


class SystemBackend(SetupBackend):  # pragma: no cover (needs the real tools)
    def _run(self, *args: str, inp: str | None = None) -> tuple[int, str]:
        try:
            p = subprocess.run(args, input=inp, capture_output=True, text=True,
                               timeout=60)
            return p.returncode, p.stdout
        except (OSError, subprocess.SubprocessError):
            return 1, ""

    def list_timezones(self) -> list[str]:
        _, out = self._run("timedatectl", "list-timezones")
        return [l.strip() for l in out.splitlines() if l.strip()]

    def set_timezone(self, tz: str) -> bool:
        return self._run("timedatectl", "set-timezone", tz)[0] == 0

    def list_keymaps(self) -> list[str]:
        _, out = self._run("localectl", "list-keymaps")
        return [l.strip() for l in out.splitlines() if l.strip()]

    def set_keymap(self, km: str) -> bool:
        return self._run("localectl", "set-keymap", km)[0] == 0

    def set_locale(self, locale: str) -> bool:
        return self._run("localectl", "set-locale", f"LANG={locale}")[0] == 0

    def has_ethernet_carrier(self) -> bool:
        import glob
        import os
        for dev in glob.glob("/sys/class/net/e*/carrier"):
            try:
                if open(dev).read().strip() == "1":
                    return True
            except OSError:
                continue
        return False

    def wifi_scan(self) -> list[WifiNetwork]:
        self._run("nmcli", "device", "wifi", "rescan")
        _, out = self._run("nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY",
                           "device", "wifi", "list")
        nets: dict[str, WifiNetwork] = {}
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) < 3 or not parts[0]:
                continue
            ssid = parts[0]
            try:
                signal = int(parts[1])
            except ValueError:
                signal = 0
            secured = bool(parts[2].strip())
            # keep the strongest sighting of each SSID
            if ssid not in nets or signal > nets[ssid].signal:
                nets[ssid] = WifiNetwork(ssid, signal, secured)
        return sorted(nets.values(), key=lambda n: -n.signal)

    def wifi_connect(self, ssid: str, psk: str | None) -> bool:
        if psk:
            return self._run("nmcli", "device", "wifi", "connect", ssid,
                             "password", psk)[0] == 0
        return self._run("nmcli", "device", "wifi", "connect", ssid)[0] == 0
