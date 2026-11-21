#!/usr/bin/env bash
# =====================================================================
# fusion-perf-baseline.sh -- remove performance-sapping Linux defaults and
# install Fusion's performance-raising configs. Run as root on target
# (or applied into airootfs at ISO build time with TARGET=<airootfs>).
#
#   fusion-perf-baseline.sh [TARGET]      # default TARGET=/
#   fusion-perf-baseline.sh --revert-mit  # drop mitigations=off only
#
# What it does:
#   * installs sysctl, journald, udev performance configs
#   * masks services that only slow boot / add idle overhead on a gaming box
#   * appends Fusion kernel cmdline to the detected bootloader
# All reversible: configs live in dedicated files; masks can be unmasked;
# cmdline edits are clearly fenced.
# =====================================================================
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
# Config source: the repo when run from a checkout, else the shipped copy that
# install-fusion-userspace.sh places on the installed system.
if [ -d "$REPO/configs/fusion-performance" ]; then
    SRC="$REPO/configs/fusion-performance"
else
    SRC="/usr/share/fusion/perf"
fi

if [ "${1:-}" = "--revert-mit" ]; then
    sed -i 's/\bmitigations=off\b//g' /etc/kernel/cmdline 2>/dev/null || true
    for f in /boot/loader/entries/*.conf /etc/default/grub; do
        [ -e "$f" ] && sed -i 's/\bmitigations=off\b//g' "$f"
    done
    echo "mitigations=off removed. Re-run your bootloader update + reboot."
    exit 0
fi

TARGET="${1:-/}"
inst() { install -Dm644 "$1" "$TARGET$2" && echo "  installed $2"; }

echo ">> installing performance configs into $TARGET"
inst "$SRC/99-fusion-performance.conf"       /etc/sysctl.d/99-fusion-performance.conf
inst "$SRC/fusion-journald.conf"             /etc/systemd/journald.conf.d/fusion.conf
inst "$SRC/60-fusion-usb-autosuspend.rules"  /etc/udev/rules.d/60-fusion-usb-autosuspend.rules

echo ">> masking services that only cost boot time / idle overhead (reversible)"
# These are safe to mask on a dedicated single-user gaming box.
MASK="NetworkManager-wait-online.service systemd-networkd-wait-online.service \
man-db.timer man-db.service plocate-updatedb.timer updatedb.timer \
systemd-journald-audit.socket"
if [ "$TARGET" = "/" ] && command -v systemctl >/dev/null; then
    for s in $MASK; do systemctl mask "$s" >/dev/null 2>&1 && echo "  masked $s"; done
else
    # ISO build: create the mask symlinks directly in the airootfs.
    install -d "$TARGET/etc/systemd/system"
    for s in $MASK; do ln -sf /dev/null "$TARGET/etc/systemd/system/$s" 2>/dev/null \
        && echo "  masked $s (airootfs)"; done
fi

echo ">> applying Fusion kernel cmdline to the bootloader"
PARAMS="$(grep -vE '^\s*#|^\s*$' "$SRC/fusion-cmdline.conf" | tr '\n' ' ')"
applied=0
# systemd-boot: /etc/kernel/cmdline or per-entry files.
if [ -f "$TARGET/etc/kernel/cmdline" ]; then
    grep -q "nowatchdog" "$TARGET/etc/kernel/cmdline" || \
        sed -i "s|\$| $PARAMS|" "$TARGET/etc/kernel/cmdline"
    echo "  updated /etc/kernel/cmdline"; applied=1
fi
for e in "$TARGET"/boot/loader/entries/*.conf; do
    [ -e "$e" ] || continue
    grep -q "nowatchdog" "$e" || sed -i "/^options / s|\$| $PARAMS|" "$e"
    echo "  updated $(basename "$e")"; applied=1
done
# GRUB.
if [ -f "$TARGET/etc/default/grub" ]; then
    if ! grep -q "nowatchdog" "$TARGET/etc/default/grub"; then
        sed -i "s|^\(GRUB_CMDLINE_LINUX_DEFAULT=\"[^\"]*\)\"|\1 $PARAMS\"|" \
            "$TARGET/etc/default/grub"
    fi
    echo "  updated /etc/default/grub (run grub-mkconfig after)"; applied=1
fi
[ "$applied" = 1 ] || echo "  ! no known bootloader config found; add cmdline manually:
    $PARAMS"

echo ">> done. Reboot for cmdline changes; sysctl/udev apply on next boot or:"
echo "   sysctl --system && udevadm control --reload"
