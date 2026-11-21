# Fusion: on tty1 login, start the gaming session. Other TTYs stay normal shells.
if [ -z "${FUSION_SESSION_STARTED:-}" ] && [ "$(tty)" = "/dev/tty1" ]; then
    export FUSION_SESSION_STARTED=1
    exec fusion-session
fi
