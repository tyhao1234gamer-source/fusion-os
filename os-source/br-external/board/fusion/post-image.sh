#!/bin/sh
# Assemble the bootable UEFI disk image with genimage.
# Runs from the Buildroot top directory; $BINARIES_DIR / $TARGET_DIR are set.
set -e

BOARD_DIR="$(dirname "$0")"
GENIMAGE_CFG="${2:-${BOARD_DIR}/genimage.cfg}"

# Place our GRUB config next to the grub EFI binary Buildroot built into the ESP.
if [ -d "${BINARIES_DIR}/efi-part/EFI/BOOT" ]; then
    install -D -m 0644 "${BOARD_DIR}/grub.cfg" \
        "${BINARIES_DIR}/efi-part/EFI/BOOT/grub.cfg"
else
    echo "post-image: expected ${BINARIES_DIR}/efi-part/EFI/BOOT (grub EFI) not found" >&2
    echo "            check BR2_TARGET_GRUB2_X86_64_EFI is enabled." >&2
fi

# Build the disk image (support/scripts/genimage.sh is in the Buildroot tree).
support/scripts/genimage.sh -c "${GENIMAGE_CFG}"

echo "post-image: wrote ${BINARIES_DIR}/fusion-os.img"
