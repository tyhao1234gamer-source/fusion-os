import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent.parent
TOOL = HERE / "live-cmdline.py"
CONF = HERE.parent / "configs" / "fusion-performance" / "fusion-cmdline.conf"

UEFI = """title    Arch Linux install medium (%ARCH%, UEFI)
sort-key 01
linux    /%INSTALL_DIR%/boot/%ARCH%/vmlinuz-linux
initrd   /%INSTALL_DIR%/boot/%ARCH%/initramfs-linux.img
options  archisobasedir=%INSTALL_DIR% archisosearchuuid=%ARCHISO_UUID%
"""
SPEECH = UEFI.replace("UEFI)", "UEFI, speech)").replace("%ARCHISO_UUID%", "%ARCHISO_UUID% accessibility=on")
SYSLINUX = """LABEL arch64
TEXT HELP
Boot the Arch Linux install medium on BIOS.
ENDTEXT
MENU LABEL Arch Linux install medium (%ARCH%, BIOS)
LINUX /%INSTALL_DIR%/boot/%ARCH%/vmlinuz-linux
INITRD /%INSTALL_DIR%/boot/%ARCH%/initramfs-linux.img
APPEND archisobasedir=%INSTALL_DIR% archisosearchuuid=%ARCHISO_UUID%

# Accessibility boot option
LABEL arch64speech
MENU LABEL Arch Linux install medium (%ARCH%, BIOS) with speech
LINUX /%INSTALL_DIR%/boot/%ARCH%/vmlinuz-linux
APPEND archisobasedir=%INSTALL_DIR% archisosearchuuid=%ARCHISO_UUID% accessibility=on
"""


class LiveCmdline(unittest.TestCase):
    def make(self):
        p = pathlib.Path(tempfile.mkdtemp())
        e = p / "efiboot" / "loader" / "entries"
        e.mkdir(parents=True)
        (e / "01-archiso-linux.conf").write_text(UEFI)
        (e / "02-archiso-speech-linux.conf").write_text(SPEECH)
        (p / "syslinux").mkdir()
        (p / "syslinux" / "archiso_sys-linux.cfg").write_text(SYSLINUX)
        return p

    def run_tool(self, p):
        return subprocess.run([sys.executable, str(TOOL), str(p), str(CONF)],
                              capture_output=True, text=True)

    def test_uefi_and_bios_entries(self):
        p = self.make()
        r = self.run_tool(p)
        self.assertEqual(r.returncode, 0, r.stderr)
        e = p / "efiboot" / "loader" / "entries"
        main = (e / "01-archiso-linux.conf").read_text()
        self.assertIn("mitigations=off", main)
        self.assertIn("nowatchdog", main)
        self.assertNotIn("tsc=reliable", main)
        safe = (e / "01-archiso-linux-safe.conf").read_text()
        self.assertIn("(safe)", safe)
        self.assertNotIn("mitigations=off", safe)
        self.assertNotIn("mitigations", (e / "02-archiso-speech-linux.conf").read_text())
        sl = (p / "syslinux" / "archiso_sys-linux.cfg").read_text()
        self.assertEqual(sl.count("LABEL arch64safe"), 1)
        self.assertEqual(sl.count("mitigations=off"), 1)       # main only
        self.assertIn("BIOS) (safe)", sl)
        self.assertLess(sl.index("arch64safe"), sl.index("# Accessibility"))
        speech = sl.split("LABEL arch64speech")[1]
        self.assertNotIn("mitigations", speech)

    def test_idempotent_params(self):
        p = self.make()
        self.run_tool(p)
        main = (p / "efiboot" / "loader" / "entries" / "01-archiso-linux.conf").read_text()
        self.assertEqual(main.count("nowatchdog"), 1)

    def test_fails_when_no_entries(self):
        p = pathlib.Path(tempfile.mkdtemp())
        self.assertNotEqual(self.run_tool(p).returncode, 0)


if __name__ == "__main__":
    unittest.main()
