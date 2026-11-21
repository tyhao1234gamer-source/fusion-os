# Fusion OS session (full edition). POSIX sh: read by busybox ash and bash.
# Only tty1 starts the console-like session; other TTYs are plain shells.
if [ "$(tty)" = "/dev/tty1" ] && [ -z "${FUSION_SESSION_STARTED:-}" ]; then
    export FUSION_SESSION_STARTED=1

    # 1. First-run screen: region, time zone, keyboard, Wi-Fi/Ethernet.
    #    No account, no sign-in. Runs once.
    [ -f /etc/fusion/.setup-done ] || sudo -n /usr/bin/fusion-setup

    # 2. Reversible performance baseline for the session.
    sudo -n /usr/bin/fusion-opt apply balanced --real >/dev/null 2>&1

    # 3. First time only: Steam, Discord, Epic (Heroic), Firefox from Flathub.
    [ -f "$HOME/.local/share/fusion/apps-installed" ] || /usr/bin/fusion-apps

    # 4. Session: Steam Big Picture fullscreen in cage (Wayland + Xwayland).
    export XDG_RUNTIME_DIR="/tmp/xdg-runtime-$(id -u)"
    mkdir -p "$XDG_RUNTIME_DIR" && chmod 0700 "$XDG_RUNTIME_DIR"
    export XDG_SESSION_TYPE=wayland
    if flatpak info com.valvesoftware.Steam >/dev/null 2>&1; then
        exec dbus-run-session -- cage -- \
            flatpak run com.valvesoftware.Steam -gamepadui
    fi

    # Fallback (no Steam yet, e.g. offline): the Fusion Gaming Shell.
    exec /usr/bin/fusion-shell
fi
