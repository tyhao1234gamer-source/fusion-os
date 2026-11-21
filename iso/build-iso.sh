#!/usr/bin/env bash
# =====================================================================
# build-iso.sh -- build the bootable Fusion OS ISO for a weak x86-64 laptop.
#
#   !!  RUN ON AN ARCH LINUX HOST (or arch container) WITH INTERNET + ROOT.  !!
#   Needs the `archiso` package (provides mkarchiso + the releng profile).
#   This CANNOT run in the Fusion dev sandbox (no network/root) -- it is the
#   recipe you run to actually produce the .iso. Output boots into the Fusion
#   gaming session (gamescope + Steam Big Picture, or the Fusion Gaming Shell).
#
#   sudo ./build-iso.sh            # -> ./out/fusion-os-*.iso
# =====================================================================
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OVERLAY="$REPO/iso/overlay"
RELENG="${RELENG:-/usr/share/archiso/configs/releng}"
WORK="${WORK:-/tmp/fusion-iso}"
OUT="${OUT:-$REPO/out}"

[ "$(id -u)" = 0 ] || { echo "run as root (mkarchiso needs it)"; exit 1; }
command -v mkarchiso >/dev/null || { echo "install 'archiso' first (pacman -S archiso)"; exit 1; }
[ -d "$RELENG" ] || { echo "releng profile not found at $RELENG"; exit 1; }

echo ">> staging a copy of the official releng profile at $WORK/profile"
rm -rf "$WORK" && mkdir -p "$WORK"
cp -r "$RELENG" "$WORK/profile"
P="$WORK/profile"

echo ">> branding (iso name / label / publisher)"
sed -i 's/^iso_name=.*/iso_name="fusion-os"/'            "$P/profiledef.sh"
sed -i 's/^iso_label=.*/iso_label="FUSION_OS"/'          "$P/profiledef.sh"
sed -i 's/^iso_publisher=.*/iso_publisher="PS4 Fusion OS"/' "$P/profiledef.sh"
sed -i 's/^iso_application=.*/iso_application="Fusion OS Gaming"/' "$P/profiledef.sh"

echo ">> appending Fusion packages to the package list"
{ echo; echo "# --- Fusion additions ---"; cat "$OVERLAY/packages.x86_64"; } >> "$P/packages.x86_64"

echo ">> enabling [multilib] repo (needed for steam, wine and all lib32-* packages)"
if grep -q '^\[multilib\]' "$P/pacman.conf"; then
    echo "   already enabled"
else
    # Uncomment the standard commented multilib block:
    #   #[multilib]            ->  [multilib]
    #   #Include = .../mirrorlist -> Include = .../mirrorlist
    sed -i 's/^#\[multilib\]/[multilib]/' "$P/pacman.conf"
    sed -i '/^\[multilib\]/{n;s/^#Include/Include/}' "$P/pacman.conf"
    grep -q '^\[multilib\]' "$P/pacman.conf" && echo "   enabled" \
        || echo "   ! could not enable multilib automatically; check pacman.conf"
fi

echo ">> overlaying airootfs files (units, skel, session, configs)"
cp -r "$OVERLAY/etc" "$OVERLAY/usr" "$P/airootfs/"

echo ">> creating the 'fusion' autologin user (uid 1000)"
printf 'fusion:x:1000:1000::/home/fusion:/bin/bash\n' >> "$P/airootfs/etc/passwd"
printf 'fusion:!*::::::\n'                            >> "$P/airootfs/etc/shadow"
printf 'fusion:x:1000:\n'                             >> "$P/airootfs/etc/group"
# add fusion to wheel for sudo (install-to-disk etc.)
sed -i 's/^wheel:x:998:.*/&fusion/; t; s/^\(wheel:x:998:\)$/\1fusion/' "$P/airootfs/etc/group" 2>/dev/null || true
install -d "$P/airootfs/home/fusion"
cp "$OVERLAY/etc/skel/.bash_profile" "$P/airootfs/home/fusion/.bash_profile"

echo ">> installing the Fusion userspace tools into airootfs"
"$REPO/scripts/install-fusion-userspace.sh" "$P/airootfs"

echo ">> applying the performance baseline into airootfs (configs, masks, cmdline)"
"$REPO/scripts/fusion-perf-baseline.sh" "$P/airootfs"

echo ">> enabling services (NetworkManager, fusion-firstboot; getty autologin via drop-in)"
install -d "$P/airootfs/etc/systemd/system/multi-user.target.wants"
ln -sf /usr/lib/systemd/system/NetworkManager.service \
    "$P/airootfs/etc/systemd/system/multi-user.target.wants/NetworkManager.service"
# fusion-firstboot runs the universal hardware auto-config on first boot.
ln -sf /etc/systemd/system/fusion-firstboot.service \
    "$P/airootfs/etc/systemd/system/multi-user.target.wants/fusion-firstboot.service"

echo ">> setting ownership of /home/fusion (profiledef file_permissions)"
python3 - "$P/profiledef.sh" <<'PY'
import sys, re
f = sys.argv[1]
s = open(f).read()
add = '  ["/home/fusion"]="1000:1000:0755"\n  ["/home/fusion/.bash_profile"]="1000:1000:0644"\n'
if "/home/fusion" not in s:
    s = re.sub(r"(file_permissions=\(\n)", r"\1" + add, s, count=1)
    open(f, "w").write(s)
    print("   added /home/fusion to file_permissions")
else:
    print("   file_permissions already has /home/fusion")
PY

echo ">> building the ISO (downloads packages; takes a while)"
mkdir -p "$OUT"
mkarchiso -v -w "$WORK/work" -o "$OUT" "$P"

echo
echo ">> done. ISO is in $OUT/"
echo "   Write it to a USB with:  dd if=$OUT/fusion-os-*.iso of=/dev/sdX bs=4M status=progress oflag=sync"
echo "   Boot the laptop from it -> it auto-logs in and starts the Fusion session."
echo "   To install to disk from the live session: run 'archinstall', then on the"
echo "   installed system run scripts/fusion-postinstall.sh."
