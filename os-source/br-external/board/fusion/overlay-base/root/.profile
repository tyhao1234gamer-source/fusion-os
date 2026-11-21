# Fusion first-source milestone: on tty1, run the first-run setup once, then
# hand off to the Gaming Shell. Other TTYs stay plain shells.
if [ -z "${FUSION_SESSION_STARTED:-}" ] && [ "$(tty)" = "/dev/tty1" ]; then
    export FUSION_SESSION_STARTED=1
    if [ ! -f /etc/fusion/.setup-done ] && command -v fusion-setup >/dev/null 2>&1; then
        fusion-setup || true
    fi
    # Apply a baseline performance profile (dry on hardware without the knobs).
    command -v fusion-opt >/dev/null 2>&1 && fusion-opt apply balanced --real 2>/dev/null
    # No gamescope/Steam in this from-source base yet -> the TUI shell.
    command -v fusion-shell >/dev/null 2>&1 && exec fusion-shell
fi
