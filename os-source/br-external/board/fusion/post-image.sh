#!/bin/sh
# Assemble the hybrid BIOS + UEFI disk image. Runs from the Buildroot top dir
# with BINARIES_DIR / BUILD_DIR set. Based on Buildroot's reference
# board/pc/post-image-efi.sh, plus a BIOS stage done like grub-bios-setup.
set -e

BOARD_DIR="$(dirname "$0")"
GENIMAGE_IN="${2:-${BOARD_DIR}/genimage.cfg}"
ESP="${BINARIES_DIR}/efi-part"
ESP_BOOT="${ESP}/EFI/BOOT"

for f in "${ESP_BOOT}/bootx64.efi" "${ESP_BOOT}/bootia32.efi" "${BINARIES_DIR}/grub.img"; do
    [ -f "$f" ] || {
        echo "post-image: $f missing (are BR2_TARGET_GRUB2_X86_64_EFI, _I386_EFI and _I386_PC on?)" >&2
        exit 1
    }
done

# GRUB's BIOS stage 1 (446 bytes of MBR code). Buildroot builds it but does
# not install it anywhere without the GRUB tools, so take it from the build.
BOOT_IMG=$(ls "${BUILD_DIR}"/grub2-*/build-i386-pc/grub-core/boot.img 2>/dev/null | head -1)
[ -f "$BOOT_IMG" ] || { echo "post-image: GRUB boot.img not found in ${BUILD_DIR}" >&2; exit 1; }

# Use the rootfs filesystem UUID as the GPT partition UUID, so the kernel can
# find root by PARTUUID on any machine / disk ordering.
UUID=$(dumpe2fs "${BINARIES_DIR}/rootfs.ext2" 2>/dev/null \
       | sed -n 's/^Filesystem UUID: *\(.*\)/\1/p')
[ -n "$UUID" ] || { echo "post-image: could not read rootfs UUID" >&2; exit 1; }

# One menu for every firmware: UEFI GRUBs read EFI/BOOT/grub.cfg, the BIOS
# GRUB reads boot/grub/grub.cfg (its prefix is "(,gpt1)/boot/grub").
sed "s/UUID_TMP/${UUID}/g" "${BOARD_DIR}/grub.cfg" > "${ESP_BOOT}/grub.cfg"
mkdir -p "${ESP}/boot/grub"
cp "${ESP_BOOT}/grub.cfg" "${ESP}/boot/grub/grub.cfg"

# genimage config with the real UUID, then build fusion-os.img.
sed "s/UUID_TMP/${UUID}/g" "${GENIMAGE_IN}" > "${BINARIES_DIR}/genimage-fusion.cfg"
support/scripts/genimage.sh -c "${BINARIES_DIR}/genimage-fusion.cfg"

# BIOS stage: GRUB boot.img into the protective MBR, pointed at core.img in
# the BIOS boot partition. Then verify it.
python3 "${BOARD_DIR}/bios-setup.py" "${BINARIES_DIR}/fusion-os.img" "$BOOT_IMG"
python3 "${BOARD_DIR}/bios-setup.py" "${BINARIES_DIR}/fusion-os.img" "$BOOT_IMG" --check

echo "post-image: wrote ${BINARIES_DIR}/fusion-os.img (BIOS + UEFI x64/ia32, root PARTUUID=${UUID})"
