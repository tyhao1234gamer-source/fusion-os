#!/bin/sh
# Runs against the assembled TARGET rootfs, just before the filesystem image.
# $1 = TARGET_DIR. Keep it minimal and idempotent.
set -e
TARGET_DIR="$1"

# Make sure our tools are on PATH and executable (the package installs them,
# this is a belt-and-braces guard).
for t in fusion-detect fusion-opt fusion-shell fusion-bench fusion-compat; do
    [ -f "$TARGET_DIR/usr/bin/$t" ] && chmod 0755 "$TARGET_DIR/usr/bin/$t" || true
done

# Friendly login banner.
cat > "$TARGET_DIR/etc/motd" <<'EOF'

  Fusion OS  -  built from source (Buildroot)
  Try: fusion-detect   |   fusion-opt list   |   fusion-shell

EOF
