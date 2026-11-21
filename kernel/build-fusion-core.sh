#!/usr/bin/env bash
# =====================================================================
# build-fusion-core.sh -- build the Fusion Core kernel from a community
# PS4 kernel tree + the fusion-core.config overlay.
#
#   !!  RUN THIS ON A BUILD HOST, NOT INSIDE THIS REPO SANDBOX  !!
#   It needs network (to clone the PS4 kernel source), a cross/native
#   x86-64 toolchain, and ~15 GB of disk. It is NOT run or verified by the
#   Fusion CI sandbox -- per the project rule, the resulting bzImage must be
#   boot-tested on a real PS4 before being called working.
#
# Choose the kernel source for YOUR southbridge (see hardware/ detection):
#   Aeolia / Belize : 6.15.x ThinLTO tree
#   Baikal          : 7.0-Clean (rmux) or 5.4.247 tree
# Set PS4_KERNEL_REPO / PS4_KERNEL_BRANCH accordingly.
# =====================================================================
set -euo pipefail

PS4_KERNEL_REPO="${PS4_KERNEL_REPO:-https://github.com/<community-ps4-kernel>/linux-ps4}"
PS4_KERNEL_BRANCH="${PS4_KERNEL_BRANCH:-6.15.4-fusion}"
OVERLAY="$(cd "$(dirname "$0")" && pwd)/fusion-core.config"
SRC="${SRC:-$PWD/linux-ps4}"
JOBS="${JOBS:-$(nproc)}"

echo ">> Fusion Core build"
echo "   repo:    $PS4_KERNEL_REPO ($PS4_KERNEL_BRANCH)"
echo "   overlay: $OVERLAY"
echo "   src:     $SRC"

if [ ! -d "$SRC/.git" ]; then
    echo ">> cloning PS4 kernel source (needs network)"
    git clone --depth 1 --branch "$PS4_KERNEL_BRANCH" "$PS4_KERNEL_REPO" "$SRC"
fi
cd "$SRC"

echo ">> starting from the tree's PS4 defconfig (preserves PS4 drivers/patches)"
# The community trees ship a ps4 defconfig; fall back to the current .config.
if [ -f arch/x86/configs/ps4_defconfig ]; then
    make ps4_defconfig
elif [ ! -f .config ]; then
    echo "!! no ps4_defconfig and no .config -- provide a base .config first" >&2
    exit 1
fi

echo ">> merging Fusion Core overlay ON TOP (does not drop PS4 symbols)"
./scripts/kconfig/merge_config.sh -m .config "$OVERLAY"
make olddefconfig

echo ">> keep a known-good recovery config/kernel before building the tuned one"
cp .config "../fusion-core-${PS4_KERNEL_BRANCH}.config.bak"

echo ">> building (this is long on anything, forever on the Jaguar -- build on a PC)"
make -j"$JOBS" bzImage

echo
echo ">> done: arch/x86/boot/bzImage"
echo "   Next: build initramfs, then boot-test via PS4-Linux-Loader + kexec."
echo "   Do NOT mark Fusion Core 'working' until it boots on the target model."
