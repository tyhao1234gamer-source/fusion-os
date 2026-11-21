#!/usr/bin/env python3
"""Make a GPT disk image BIOS-bootable with GRUB, like grub-bios-setup.

    bios-setup.py <disk.img> <boot.img> [--check]

The image must already contain GRUB's core.img (grub-mkimage -O i386-pc) in
its "BIOS boot" GPT partition. This writes GRUB's 446-byte stage 1 into the
protective MBR, keeping the partition table and signature, and points stage 1
and core.img's first blocklist at that partition.

Offsets are GRUB's own (include/grub/i386/pc/boot.h, boot/i386/pc/diskboot.S):
  boot.img 0x5C  kernel_sector    LE64: first sector of core.img
  boot.img 0x64  boot_drive       0xFF = use the drive the BIOS booted (DL)
  boot.img 0x66  drive check jump NOP NOP, as grub-setup does for hard disks
  core.img 0x1F4 first blocklist  LE64 start, LE16 length (set by mkimage)

--check only verifies an image that was already set up (used by tests).
"""
import struct
import sys
import uuid

SECTOR = 512
BIOS_BOOT = uuid.UUID("21686148-6449-6e61-6f74-656e65656646")

KERNEL_SECTOR = 0x5C
BOOT_DRIVE = 0x64
DRIVE_CHECK = 0x66
BPB_START, BPB_END = 0x03, 0x5A
NT_MAGIC, PART_END = 0x1B8, 0x1FE
LIST = 0x200 - 12


def find_bios_boot(img):
    img.seek(SECTOR)
    hdr = img.read(SECTOR)
    if hdr[:8] != b"EFI PART":
        sys.exit("bios-setup: no GPT header at LBA 1")
    entries_lba, count, size = struct.unpack_from("<QII", hdr, 72)
    img.seek(entries_lba * SECTOR)
    table = img.read(count * size)
    for i in range(count):
        ent = table[i * size:(i + 1) * size]
        if uuid.UUID(bytes_le=ent[:16]) == BIOS_BOOT:
            first, last = struct.unpack_from("<QQ", ent, 32)
            return i + 1, first, last
    sys.exit("bios-setup: no BIOS boot partition in the GPT")


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    check = "--check" in argv
    with open(argv[2], "rb") as f:
        boot = bytearray(f.read())
    if len(boot) != SECTOR or boot[0x1FE:] != b"\x55\xaa":
        sys.exit("bios-setup: boot.img is not a 512-byte boot sector")

    with open(argv[1], "r+b") as img:
        num, first, last = find_bios_boot(img)
        img.seek(0)
        mbr = bytearray(img.read(SECTOR))
        img.seek(first * SECTOR)
        core = bytearray(img.read(SECTOR))
        start, length = struct.unpack_from("<QH", core, LIST)
        if length == 0:
            sys.exit("bios-setup: core.img blocklist length is 0 (not a grub-mkimage i386-pc image?)")
        if first + 1 + length > last + 1:
            sys.exit("bios-setup: core.img does not fit in the BIOS boot partition")

        if check:
            ok = (struct.unpack_from("<Q", mbr, KERNEL_SECTOR)[0] == first
                  and mbr[BOOT_DRIVE] == 0xFF
                  and mbr[DRIVE_CHECK:DRIVE_CHECK + 2] == b"\x90\x90"
                  and mbr[0x1BE + 4] == 0xEE
                  and mbr[0x1FE:] == b"\x55\xaa"
                  and start == first + 1)
            print(f"bios-setup check: {'OK' if ok else 'FAILED'} "
                  f"(BIOS boot = gpt{num}, sectors {first}-{last}, core {length + 1} sectors)")
            return 0 if ok else 1

        if mbr[0x1BE + 4] != 0xEE:
            sys.exit("bios-setup: sector 0 is not a GPT protective MBR")
        # Keep what grub-setup keeps from the existing sector.
        boot[BPB_START:BPB_END] = mbr[BPB_START:BPB_END]
        boot[NT_MAGIC:PART_END] = mbr[NT_MAGIC:PART_END]
        struct.pack_into("<Q", boot, KERNEL_SECTOR, first)
        boot[BOOT_DRIVE] = 0xFF
        boot[DRIVE_CHECK:DRIVE_CHECK + 2] = b"\x90\x90"
        struct.pack_into("<Q", core, LIST, first + 1)

        img.seek(0)
        img.write(boot)
        img.seek(first * SECTOR)
        img.write(core)
    print(f"bios-setup: GRUB stage 1 -> MBR, core.img at sector {first} (gpt{num}), "
          f"{length + 1} sectors")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
