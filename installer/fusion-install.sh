#!/usr/bin/env bash
# =====================================================================
# fusion-install.sh -- assemble a PS4 Fusion OS image (loader trio).
#
# PS4 Linux does NOT boot a normal PC ISO. It boots a trio:
#     bzImage  + initramfs  + rootfs(.tar.xz)
# loaded by PS4-Linux-Loader + ps4-kexec from a jailbroken console, onto an
# external USB drive (or a carved partition; internal HDD not available on
# Baikal). This script assembles that trio from a built rootfs and kernel.
#
#   !!  Parts of this need root and a real toolchain/rootfs and are NOT run
#       by the Fusion sandbox. The hardware-detection and layout steps are
#       real; image build steps are marked [TARGET].  !!
# =====================================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"

OUT="${OUT:-$PWD/fusion-image}"
ROOTFS_SRC="${ROOTFS_SRC:-}"          # path to a prepared Arch/CachyOS rootfs dir
BZIMAGE="${BZIMAGE:-}"                # path to a built Fusion Core bzImage

echo "== PS4 Fusion OS installer =="

# --- 1. Detect hardware and choose kernel / Mesa pin (REAL) -----------
echo ">> detecting hardware"
REC="$(python3 "$HERE/hardware/fusion-detect")" || true
echo "$REC"
SB="$(printf '%s' "$REC" | python3 -c 'import sys,json;print(json.load(sys.stdin)["southbridge"])' 2>/dev/null || echo UNKNOWN)"
if [ "$SB" = "UNKNOWN" ]; then
    echo "!! Southbridge unknown. Run on the PS4, or pass it explicitly."
    echo "   Aborting rather than guessing a kernel (project rule)."
    [ "${FORCE:-0}" = "1" ] || exit 1
fi

# --- 2. Prepare output layout (REAL) ----------------------------------
echo ">> preparing $OUT"
mkdir -p "$OUT"/{boot,rootfs}

# --- 3. Kernel + initramfs [TARGET] -----------------------------------
if [ -n "$BZIMAGE" ] && [ -f "$BZIMAGE" ]; then
    cp "$BZIMAGE" "$OUT/boot/bzImage"
    echo ">> copied bzImage"
else
    echo "[TARGET] build the kernel first: kernel/build-fusion-core.sh"
fi
echo "[TARGET] build initramfs (mkinitcpio) including PS4 amdgpu firmware + evdev"

# --- 4. Rootfs -> psxitarch-compatible tarball [TARGET] ---------------
if [ -n "$ROOTFS_SRC" ] && [ -d "$ROOTFS_SRC" ]; then
    echo ">> installing Fusion userspace into rootfs"
    install -Dm755 "$HERE/compatibility-manager/fusion-compat" "$ROOTFS_SRC/usr/bin/fusion-compat"
    install -Dm755 "$HERE/optimizer/fusion-opt"               "$ROOTFS_SRC/usr/bin/fusion-opt"
    install -Dm755 "$HERE/benchmarks/fusion-bench"            "$ROOTFS_SRC/usr/bin/fusion-bench"
    install -Dm755 "$HERE/gaming-shell/fusion-shell"          "$ROOTFS_SRC/usr/bin/fusion-shell"
    install -Dm755 "$HERE/hardware/fusion-detect"             "$ROOTFS_SRC/usr/bin/fusion-detect"
    # (the python packages beside each script must be copied too; see docs)
    install -Dm644 "$HERE/configs/99-fusion-sysctl.conf" "$ROOTFS_SRC/etc/sysctl.d/99-fusion.conf"
    install -Dm644 "$HERE/configs/zram-generator.conf"   "$ROOTFS_SRC/etc/systemd/zram-generator.conf"
    install -Dm644 "$HERE/configs/fusion-shell.service"  "$ROOTFS_SRC/etc/systemd/system/fusion-shell.service"
    echo "[TARGET] tar -cJf $OUT/rootfs/psxitarch.tar.xz -C $ROOTFS_SRC ."
else
    echo "[TARGET] provide ROOTFS_SRC=<prepared Arch/CachyOS rootfs dir>"
fi

echo
echo ">> layout ready at $OUT"
echo "   Copy bzImage + initramfs + psxitarch.tar.xz to a FAT32 USB and boot"
echo "   via PS4-Linux-Loader on the jailbroken console."
echo "   NOTHING here is 'done' until it boots on the target model."
