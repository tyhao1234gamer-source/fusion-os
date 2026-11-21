"""bios-setup.py on a synthetic GPT image (layout as written by genimage)."""
import os
import struct
import subprocess
import sys
import tempfile
import unittest
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "..", "br-external", "board", "fusion", "bios-setup.py")
ESP = uuid.UUID("c12a7328-f81f-11d2-ba4b-00a0c93ec93b")
BIOS = uuid.UUID("21686148-6449-6e61-6f74-656e65656646")
S = 512


def make_disk(path, bios_first=133120, bios_last=135167, core_len=60):
    size = (bios_last + 4096) * S
    with open(path, "wb") as f:
        f.truncate(size)
        mbr = bytearray(S)
        mbr[0x1B8:0x1BC] = b"\xde\xad\xbe\xef"           # disk signature
        mbr[0x1BE + 4] = 0xEE                              # protective entry
        struct.pack_into("<II", mbr, 0x1BE + 8, 1, size // S - 1)
        mbr[0x1FE:] = b"\x55\xaa"
        f.seek(0); f.write(mbr)
        hdr = bytearray(S)
        hdr[:8] = b"EFI PART"
        struct.pack_into("<QII", hdr, 72, 2, 128, 128)
        f.seek(S); f.write(hdr)
        ents = bytearray(128 * 128)
        ents[0:16] = ESP.bytes_le
        struct.pack_into("<QQ", ents, 32, 2048, 133119)
        ents[128:144] = BIOS.bytes_le
        struct.pack_into("<QQ", ents, 128 + 32, bios_first, bios_last)
        f.seek(2 * S); f.write(ents)
        core = bytearray(S)                                 # diskboot sector
        struct.pack_into("<QHH", core, 0x1F4, 2, core_len, 0x820)
        f.seek(bios_first * S); f.write(core)


def make_boot(path):
    b = bytearray(S)
    b[0:2] = b"\xeb\x63"
    struct.pack_into("<Q", b, 0x5C, 1)
    b[0x64] = 0x80
    b[0x66:0x68] = b"\xeb\x05"
    b[0x100:0x104] = b"CODE"
    b[0x1FE:] = b"\x55\xaa"
    with open(path, "wb") as f:
        f.write(b)


def run(*args):
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)


class BiosSetup(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.img = os.path.join(self.d, "disk.img")
        self.boot = os.path.join(self.d, "boot.img")
        make_boot(self.boot)

    def test_patches_like_grub_setup(self):
        make_disk(self.img)
        r = run(self.img, self.boot)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = open(self.img, "rb").read()
        mbr = data[:S]
        self.assertEqual(mbr[0x100:0x104], b"CODE")                 # stage 1 code
        self.assertEqual(struct.unpack_from("<Q", mbr, 0x5C)[0], 133120)
        self.assertEqual(mbr[0x64], 0xFF)
        self.assertEqual(mbr[0x66:0x68], b"\x90\x90")
        self.assertEqual(mbr[0x1B8:0x1BC], b"\xde\xad\xbe\xef")     # kept
        self.assertEqual(mbr[0x1BE + 4], 0xEE)                      # GPT kept
        self.assertEqual(mbr[0x1FE:], b"\x55\xaa")
        start, length, seg = struct.unpack_from("<QHH", data, 133120 * S + 0x1F4)
        self.assertEqual((start, length, seg), (133121, 60, 0x820))
        self.assertEqual(data[S:S + 8], b"EFI PART")                # GPT untouched
        self.assertEqual(run(self.img, self.boot, "--check").returncode, 0)

    def test_check_fails_before_setup(self):
        make_disk(self.img)
        self.assertNotEqual(run(self.img, self.boot, "--check").returncode, 0)

    def test_refuses_core_too_big(self):
        make_disk(self.img, core_len=5000)
        r = run(self.img, self.boot)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not fit", r.stderr)

    def test_refuses_empty_core(self):
        make_disk(self.img, core_len=0)
        self.assertNotEqual(run(self.img, self.boot).returncode, 0)

    def test_refuses_non_gpt(self):
        with open(self.img, "wb") as f:
            f.write(b"\0" * (S * 64))
        r = run(self.img, self.boot)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no GPT", r.stderr)


if __name__ == "__main__":
    unittest.main()
