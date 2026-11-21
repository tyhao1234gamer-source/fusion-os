#!/usr/bin/env bash
# =====================================================================
# fusion-postinstall.sh -- turn a fresh, minimal Arch install into Fusion OS.
# Run this ON THE INSTALLED SYSTEM (after `archinstall` minimal), as root,
# with internet. Idempotent-ish: safe to re-run.
# =====================================================================
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"

[ "$(id -u)" = 0 ] || { echo "run as root"; exit 1; }

echo ">> installing the Fusion gaming stack (needs internet + multilib enabled)"
echo "   (ensure [multilib] is enabled in /etc/pacman.conf)"
pacman -Sy --needed --noconfirm $(grep -vE '^\s*#|^\s*$' "$REPO/iso/overlay/packages.x86_64" | tr '\n' ' ') || {
    echo "!! some packages failed (AUR-only ones like dxvk-bin/xpadneo-dkms need an AUR helper)."
    echo "   Core stack should be in; install AUR extras manually."
}

echo ">> installing Fusion userspace tools + configs"
"$REPO/scripts/install-fusion-userspace.sh" "/"

echo ">> applying the performance baseline (configs, service masks, kernel cmdline)"
"$REPO/scripts/fusion-perf-baseline.sh" "/"

echo ">> creating fusion user if missing"
id fusion >/dev/null 2>&1 || useradd -m -G wheel,video,input -s /bin/bash fusion
install -Dm644 "$REPO/iso/overlay/etc/skel/.bash_profile" /home/fusion/.bash_profile
chown fusion:fusion /home/fusion/.bash_profile

echo ">> enabling autologin on tty1 + services"
install -Dm644 "$REPO/iso/overlay/etc/systemd/system/getty@tty1.service.d/autologin.conf" \
    /etc/systemd/system/getty@tty1.service.d/autologin.conf
install -Dm644 "$REPO/iso/overlay/etc/systemd/system/fusion-firstboot.service" \
    /etc/systemd/system/fusion-firstboot.service
systemctl enable NetworkManager.service 2>/dev/null || true
systemctl enable fusion-firstboot.service 2>/dev/null || true
# zram-generator.conf is already installed by install-fusion-userspace.sh

echo ">> running the universal hardware auto-config now"
/usr/bin/fusion-firstboot || true

echo
echo ">> Fusion OS post-install done. Reboot -> auto-login -> gaming session."
echo "   Try:  fusion-opt list   |   fusion-game --profile extreme -- <game>"
