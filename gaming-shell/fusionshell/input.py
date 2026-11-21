"""Optional gamepad input via Linux evdev (/dev/input/event*).

No third-party deps: we read the raw evdev input_event struct with `struct`.
If no gamepad is present (or we can't open one), the shell falls back to the
keyboard. This keeps the controller-first UX the directive asks for while
staying dependency-free and degrading gracefully.

Mapping is deliberately minimal and configurable: D-pad / left-stick vertical
-> up/down; South button (A) -> launch; North (Y) -> profile; East (B) -> quit.
Button codes vary by controller; the defaults match the DualShock 4, which is
the natural pad for a PS4.
"""

from __future__ import annotations

import os
import struct

# struct input_event: timeval (2x long) + type(u16) + code(u16) + value(i32)
_EV_FORMAT = "llHHi"
_EV_SIZE = struct.calcsize(_EV_FORMAT)

EV_KEY = 0x01
EV_ABS = 0x03

# DualShock 4 (evdev) button codes.
BTN_SOUTH = 0x130   # A / Cross   -> launch
BTN_EAST = 0x131    # B / Circle  -> quit
BTN_NORTH = 0x133   # Y / Triangle-> profile
ABS_HAT0Y = 0x11    # D-pad vertical


def open_first_gamepad(prefix: str = "/dev/input"):
    """Return an open fd for the first readable event device, or None."""
    try:
        names = sorted(n for n in os.listdir(prefix) if n.startswith("event"))
    except OSError:
        return None
    for n in names:
        path = os.path.join(prefix, n)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            return fd
        except OSError:
            continue
    return None


def decode(data: bytes) -> str | None:
    """Translate one raw evdev event into a shell action, or None."""
    if len(data) < _EV_SIZE:
        return None
    _, _, etype, code, value = struct.unpack(_EV_FORMAT, data[:_EV_SIZE])
    if etype == EV_KEY and value == 1:  # key down
        return {BTN_SOUTH: "launch", BTN_EAST: "quit",
                BTN_NORTH: "profile"}.get(code)
    if etype == EV_ABS and code == ABS_HAT0Y:
        if value < 0:
            return "up"
        if value > 0:
            return "down"
    return None


def poll(fd, timeout_ms: int = 50) -> str | None:  # pragma: no cover (needs device)
    import select

    r, _, _ = select.select([fd], [], [], timeout_ms / 1000.0)
    if not r:
        return None
    try:
        data = os.read(fd, _EV_SIZE)
    except OSError:
        return None
    return decode(data)
