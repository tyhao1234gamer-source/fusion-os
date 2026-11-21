#!/usr/bin/env bash
# =====================================================================
# fusion-firstboot.sh -- runs ONCE on the first boot of a Fusion system
# (live or installed), detects the actual hardware, and configures the
# machine to extract its maximum performance. Then disables itself.
#
# This is what makes Fusion OS universal: the same image adapts to whatever
# laptop or PC it boots on.
#
# Driven entirely by `fusion-detect --json`. Idempotent and safe to re-run.
# =====================================================================
set -u
STAMP=/etc/fusion/.firstboot-done
mkdir -p /etc/fusion
[ -f "$STAMP" ] && { echo "firstboot already done"; exit 0; }

echo ">> Fusion first boot: detecting hardware"
REPORT="$(fusion-detect --json)" || { echo "detect failed"; exit 1; }
echo "$REPORT" > /etc/fusion/machine.json
echo "   saved /etc/fusion/machine.json"

jqget() { python3 -c "import json,sys; print(json.load(open('/etc/fusion/machine.json'))$1)" 2>/dev/null; }

# --- 1. Per-disk IO scheduler via udev (from the tuning plan) ----------
echo ">> writing IO scheduler udev rules"
RULE=/etc/udev/rules.d/60-fusion-ioscheduler.rules
: > "$RULE"
python3 - <<'PY' >> "$RULE"
import json
t = json.load(open('/etc/fusion/machine.json'))['tuning']['io_scheduler']
for disk, sched in t.items():
    # match by kernel name; set the scheduler when the device appears
    print(f'ACTION=="add|change", KERNEL=="{disk}", '
          f'ATTR{{queue/scheduler}}="{sched}"')
PY
echo "   wrote $RULE"

# --- 2. zram size from detected RAM -----------------------------------
ZRAM_MB="$(jqget "['tuning']['zram_mb']")"
if [ -n "${ZRAM_MB:-}" ] && [ "${ZRAM_MB:-0}" -gt 0 ] 2>/dev/null; then
    echo ">> setting zram size to ${ZRAM_MB} MB"
    cat > /etc/systemd/zram-generator.conf <<EOF
[zram0]
zram-size = ${ZRAM_MB}
compression-algorithm = zstd
swap-priority = 100
fs-type = swap
EOF
fi

# --- 3. GPU driver: install NVIDIA proprietary if detected + online ---
NVIDIA="$(jqget "['drivers']['nvidia_proprietary']")"
if [ "${NVIDIA:-False}" = "True" ]; then
    echo ">> NVIDIA GPU detected"
    if ping -c1 -W2 archlinux.org >/dev/null 2>&1 && command -v pacman >/dev/null; then
        echo "   installing proprietary NVIDIA driver"
        pacman -Sy --needed --noconfirm nvidia-dkms nvidia-utils lib32-nvidia-utils \
            && echo "options nvidia-drm modeset=1" > /etc/modprobe.d/nvidia-drm.conf \
            && echo "   NVIDIA driver installed; modeset enabled"
    else
        echo "   offline or no pacman: nouveau stays active. Run later:"
        echo "     sudo pacman -S nvidia-dkms nvidia-utils lib32-nvidia-utils"
    fi
fi

# --- 4. AVX2 warning surfaced to the user -----------------------------
if python3 -c "import json;import sys;sys.exit(0 if json.load(open('/etc/fusion/machine.json'))['machine']['cpu']['has_avx2'] else 1)"; then :; else
    echo ">> NOTE: this CPU has no AVX2; some modern titles will not run (hardware limit)."
fi

udevadm control --reload 2>/dev/null || true
touch "$STAMP"
echo ">> Fusion first boot complete. 'fusion-detect' shows the machine any time."
