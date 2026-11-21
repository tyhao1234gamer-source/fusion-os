# Fusion OS session (full edition). POSIX sh: read by busybox ash and bash.
# Only tty1 starts the console-like session; other TTYs are plain shells.
if [ "$(tty)" = "/dev/tty1" ] && [ -z "${FUSION_SESSION_STARTED:-}" ]; then
    export FUSION_SESSION_STARTED=1

    # 1. First-run screen: region, time zone, keyboard, Wi-Fi/Ethernet.
    #    No account, no sign-in. Runs once.
    [ -f /etc/fusion/.setup-done ] || sudo -n /usr/bin/fusion-setup

    # 2. Reversible performance baseline for the session.
    sudo -n /usr/bin/fusion-opt apply balanced --real >/dev/null 2>&1

    # 3. First time only: Steam, Discord, Epic (Heroic), Firefox, MangoHud and
    #    gamescope from Flathub. Steam is installed; logging into it is up to
    #    the user, later, inside Steam.
    [ -f "$HOME/.local/share/fusion/apps-installed" ] || /usr/bin/fusion-apps

    # 4. The Fusion menu: Steam first, then Discord, Epic, Firefox and any
    #    Windows games added with fusion-compat. Each app opens fullscreen
    #    (fusion-launch starts the compositor); closing it ends this login,
    #    getty logs in again and the menu comes back.
    exec /usr/bin/fusion-shell
fi
