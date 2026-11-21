#!/usr/bin/env bash
# =====================================================================
# install-fusion-userspace.sh -- copy the Fusion tools + their Python
# packages + system configs into a target root filesystem.
#
# Used by BOTH:
#   * the ISO build (target = airootfs), and
#   * fusion-postinstall.sh (target = a freshly installed system, "/").
#
# Pure file copy; no network. Installs the four stdlib-only tools so they run
# with just python3 present.
#
#   install-fusion-userspace.sh <TARGET_ROOT>
# =====================================================================
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:?usage: install-fusion-userspace.sh <TARGET_ROOT>}"

LIB="$TARGET/usr/lib/fusion"
BIN="$TARGET/usr/bin"
install -d "$LIB" "$BIN"

echo ">> installing Fusion Python packages into $LIB"
cp -r "$REPO/compatibility-manager/fusioncompat" "$LIB/"
cp -r "$REPO/optimizer/fusionopt"               "$LIB/"
cp -r "$REPO/benchmarks/fusionbench"            "$LIB/"
cp -r "$REPO/gaming-shell/fusionshell"          "$LIB/"
cp -r "$REPO/hardware/fusionhw"                 "$LIB/"
# ship the curated compat seed too
install -Dm644 "$REPO/compatibility-manager/profiles/compatdb.seed.json" \
    "$TARGET/usr/share/fusion/compatdb.seed.json"

echo ">> installing entry-point wrappers into $BIN (they add /usr/lib/fusion to sys.path)"
mk() { # mk <name> <module.cli>
    cat > "$BIN/$1" <<EOF
#!/usr/bin/env python3
import sys; sys.path.insert(0, "/usr/lib/fusion")
from $2 import main
raise SystemExit(main())
EOF
    chmod +x "$BIN/$1"
}
mk fusion-compat fusioncompat.cli
mk fusion-opt    fusionopt.cli
mk fusion-bench  fusionbench.cli
mk fusion-shell  fusionshell.cli

# fusion-detect: a thin wrapper that finds fusionhw in /usr/lib/fusion.
cat > "$BIN/fusion-detect" <<'EOF'
#!/usr/bin/env python3
import sys; sys.path.insert(0, "/usr/lib/fusion")
import argparse, json
from fusionhw.detect import classify, detect
p = argparse.ArgumentParser(prog="fusion-detect")
p.add_argument("--pci", nargs="*")
a = p.parse_args()
rec = classify([tuple(x.lower().split(":")) for x in a.pci]) if a.pci else detect()
print(json.dumps(rec.as_dict(), indent=2))
EOF
chmod +x "$BIN/fusion-detect"

# fusion-game is a bash script; copy and patch its relative lookups since on the
# installed system everything lives in /usr/bin.
install -Dm755 "$REPO/optimizer/fusion-game" "$BIN/fusion-game"
sed -i 's#"\$HERE/../compatibility-manager/fusion-compat"#fusion-compat#g; s#"\$HERE/fusion-opt"#fusion-opt#g; s#PYTHONPATH="\$HERE"#PYTHONPATH=/usr/lib/fusion#g' \
    "$BIN/fusion-game"

echo ">> installing system configs"
install -Dm644 "$REPO/configs/99-fusion-sysctl.conf" "$TARGET/etc/sysctl.d/99-fusion.conf"
install -Dm644 "$REPO/configs/zram-generator.conf"   "$TARGET/etc/systemd/zram-generator.conf"
install -Dm644 "$REPO/graphics/fusion-graphics.env"  "$TARGET/etc/environment.d/90-fusion-graphics.conf"
install -Dm755 "$REPO/iso/overlay/usr/local/bin/fusion-session" "$BIN/fusion-session" 2>/dev/null || true

echo ">> done. Tools in $BIN: fusion-compat fusion-opt fusion-bench fusion-shell fusion-detect fusion-game"
