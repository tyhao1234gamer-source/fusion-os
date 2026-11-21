#!/usr/bin/env bash
# =====================================================================
# build-in-docker.sh -- build the Fusion OS ISO on ANY machine with Docker
# (Windows/Mac/Linux). No Arch install needed: it runs the whole build inside
# an official Arch container. Needs Docker + internet (the container downloads
# the packages).
#
#   ./iso/build-in-docker.sh            # -> ./out/fusion-os-*.iso
#
# --privileged is required because mkarchiso creates loop devices / mounts.
# =====================================================================
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

command -v docker >/dev/null || { echo "Docker is required. Install Docker Desktop (Win/Mac) or docker (Linux)."; exit 1; }

echo ">> building Fusion OS ISO inside an Arch container (this downloads packages)"
docker run --privileged --rm \
    -v "$REPO:/repo" \
    archlinux:latest \
    bash -c '
        set -euo pipefail
        pacman -Sy --noconfirm --needed archiso python
        chmod +x /repo/iso/build-iso.sh /repo/scripts/*.sh 2>/dev/null || true
        OUT=/repo/out /repo/iso/build-iso.sh
    '

echo
echo ">> done. ISO is in $REPO/out/"
ls -lh "$REPO/out/"*.iso 2>/dev/null || true
echo "   Write to USB:  sudo dd if=out/fusion-os-*.iso of=/dev/sdX bs=4M status=progress oflag=sync"
echo "   (on Windows use Rufus or balenaEtcher to write the .iso to the USB)"
