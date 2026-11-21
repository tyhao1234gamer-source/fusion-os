#!/bin/sh
# Assemble the bootable UEFI disk image. Runs from the Buildroot top dir with
# BINARIES_DIR set. Mirrors Buildroot's reference board/pc/post-image-efi.sh.
set -e

BOARD_DIR="$(dirname "$0")"
GENIMAGE_IN="${2:-${BOARD_DIR}/genimage.cfg}"
ESP_BOOT="${BINARIES_DIR}/efi-part/EFI/BOOT"

[ -f "${ESP_BOOT}/bootx64.efi" ] || {
    echo "post-image: ${ESP_BOOT}/bootx64.efi missing (is BR2_TARGET_GRUB2_X86_64_EFI on?)" >&2
    exit 1
}

# Use the rootfs filesystem UUID as the GPT partition UUID, so the kernel can
# find root by PARTUUID on any machine / disk ordering.
UUID=$(dumpe2fs "${BINARIES_DIR}/rootfs.ext2" 2>/dev/null \
       | sed -n 's/^Filesystem UUID: *\(.*\)/\1/p')
[ -n "$UUID" ] || { echo "post-image: could not read rootfs UUID" >&2; exit 1; }

# Our GRUB menu, with the real UUID.
sed "s/UUID_TMP/${UUID}/g" "${BOARD_DIR}/grub.cfg" > "${ESP_BOOT}/grub.cfg"

# genimage config with the real UUID, then build fusion-os.img.
sed "s/UUID_TMP/${UUID}/g" "${GENIMAGE_IN}" > "${BINARIES_DIR}/genimage-fusion.cfg"
support/scripts/genimage.sh -c "${BINARIES_DIR}/genimage-fusion.cfg"

echo "post-image: wrote ${BINARIES_DIR}/fusion-os.img (root PARTUUID=${UUID})"
