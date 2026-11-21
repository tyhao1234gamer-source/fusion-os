"""Pure parts of fusion-install-disk (layout, device names, disk labels, GRUB
retarget). The destructive part needs real disks and is NOT covered here."""
import os
import subprocess
import tempfile
import unittest

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "br-external",
                    "board", "fusion", "rootfs-overlay", "usr", "sbin", "fusion-install-disk")

DUMP = """label: gpt
label-id: 1B2C3D4E-0000-4000-8000-000000000001
device: /dev/sdb
unit: sectors
first-lba: 34
last-lba: 62521310
sector-size: 512

/dev/sdb1 : start=        2048, size=      131072, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B, uuid=AAAAAAAA-0000-4000-8000-000000000001, attrs="LegacyBIOSBootable"
/dev/sdb2 : start=      133120, size=        2048, type=21686148-6449-6E61-6F74-656E65656646, uuid=AAAAAAAA-0000-4000-8000-000000000002
/dev/sdb3 : start=      135168, size=    62386143, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709, uuid=AAAAAAAA-0000-4000-8000-000000000003
"""


def sh(script, stdin=""):
    for shell in ("dash", "sh"):
        r = subprocess.run([shell, "-c", f'FUSION_INSTALL_LIB=1; . "{TOOL}"; {script}'],
                           input=stdin, capture_output=True, text=True)
        return r


class InstallDisk(unittest.TestCase):
    def test_layout_keeps_boot_partitions_and_grows_root(self):
        r = sh('make_layout NEW-UUID', DUMP)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), [
            "label: gpt", "unit: sectors",
            "start=2048, size=131072, type=C12A7328-F81F-11D2-BA4B-00A0C93EC93B",
            "start=133120, size=2048, type=21686148-6449-6E61-6F74-656E65656646",
            "start=135168, type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709, uuid=NEW-UUID",
        ])
        self.assertNotIn("AAAAAAAA", r.stdout)       # every old UUID dropped

    def test_layout_accepts_old_root_type(self):
        dump = DUMP.replace("4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709",
                            "44479540-F297-41B2-9AF7-D131D5F0458A")
        r = sh('make_layout X', dump)
        self.assertEqual(r.returncode, 0)
        self.assertIn("type=4F68BCE3-E8CD-4DB1-96E7-FBCAF984B709, uuid=X", r.stdout)

    def test_layout_rejects_foreign_disks(self):
        self.assertNotEqual(sh('make_layout X', DUMP.replace("label: gpt", "label: dos")).returncode, 0)
        lines = [l for l in DUMP.splitlines() if "sdb2" not in l]
        self.assertNotEqual(sh('make_layout X', "\n".join(lines) + "\n").returncode, 0)

    def test_partdev(self):
        r = sh('partdev /dev/sda 1; partdev /dev/nvme0n1 3; partdev /dev/mmcblk0 2')
        self.assertEqual(r.stdout.split(), ["/dev/sda1", "/dev/nvme0n1p3", "/dev/mmcblk0p2"])

    def test_disk_kind(self):
        r = sh('disk_kind nvme0n1 nvme 0; disk_kind sda sata 1; disk_kind sdb sata 0; '
               'disk_kind sdc usb 0; disk_kind mmcblk0 "" 0')
        self.assertEqual(r.stdout.splitlines(),
                         ["SSD NVMe", "HDD (disco rigido)", "SSD", "USB", "eMMC/SD"])

    def test_retarget_grub_both_menus(self):
        d = tempfile.mkdtemp()
        os.makedirs(f"{d}/EFI/BOOT"); os.makedirs(f"{d}/boot/grub")
        for p in (f"{d}/EFI/BOOT/grub.cfg", f"{d}/boot/grub/grub.cfg"):
            with open(p, "w") as f:
                f.write("linux /bzImage root=PARTUUID=old-1 rootwait\n")
        r = sh(f'retarget_grub {d} old-1 new-2')
        self.assertEqual(r.returncode, 0, r.stderr)
        for p in (f"{d}/EFI/BOOT/grub.cfg", f"{d}/boot/grub/grub.cfg"):
            self.assertIn("root=PARTUUID=new-2", open(p).read())

    def test_running_with_lib_flag_does_not_run_main(self):
        r = subprocess.run(["dash", TOOL], env={**os.environ, "FUSION_INSTALL_LIB": "1"},
                           capture_output=True, text=True)
        self.assertNotIn("Fusion OS - instalar", r.stdout)

    def test_cleanup_trap_keeps_success_status(self):
        # The real trap line, run after a successful "install".
        line = next(l for l in open(TOOL) if l.strip().startswith("trap 'rc=$?"))
        script = ("set -eu\nwork=$(mktemp -d)\nmkdir -p $work/esp $work/new $work/old\n"
                  "main() {\n" + line + "echo ok; }\nmain\nexit 0\n")
        r = subprocess.run(["dash", "-c", script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
