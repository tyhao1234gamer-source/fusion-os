# Fusion: on tty1, run the first-run setup screen once, then start the gaming
# session. Other TTYs stay normal shells.
if [ -z "${FUSION_SESSION_STARTED:-}" ] && [ "$(tty)" = "/dev/tty1" ]; then
    export FUSION_SESSION_STARTED=1
    # First-run screen: region, timezone, keyboard, Wi-Fi/Ethernet. No account.
    # fusion-setup exits immediately if already configured.
    if [ ! -f /etc/fusion/.setup-done ]; then
        sudo -n fusion-setup 2>/dev/null || fusion-setup || true
    fi
    exec fusion-session
fi
