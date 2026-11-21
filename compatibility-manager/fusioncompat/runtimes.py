"""Discovery of Wine / Proton runtimes installed on the system.

Scans a configurable set of roots so it is fully testable against a fake tree
(pass `roots=[...]`) and works unprivileged. A runtime is recognised by its
launcher:

* Wine   -- a `bin/wine` (or `bin/wine64`) executable under the runtime dir.
* Proton -- a `proton` entry script at the runtime root.

The Fusion default roots follow the Arch/CachyOS layout Fusion OS ships:
    /opt/fusion/runtimes/wine/<name>/
    /opt/fusion/runtimes/proton/<name>/
plus the usual Steam compat-tools and user-local dirs.
"""

from __future__ import annotations

import os

from .models import Runtime, RuntimeKind

DEFAULT_ROOTS = [
    "/opt/fusion/runtimes/wine",
    "/opt/fusion/runtimes/proton",
    os.path.expanduser("~/.steam/steam/steamapps/common"),
    os.path.expanduser("~/.steam/steam/compatibilitytools.d"),
    os.path.expanduser("~/.local/share/fusion/runtimes"),
]


def _wine_launcher(d: str) -> str | None:
    for cand in ("bin/wine64", "bin/wine"):
        p = os.path.join(d, cand)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def _proton_launcher(d: str) -> str | None:
    p = os.path.join(d, "proton")
    if os.path.isfile(p):
        return p
    return None


def _guess_version(name: str) -> str:
    # Pull the first dotted/number-ish token out of a runtime dir name.
    import re

    m = re.search(r"(\d+[\w.\-]*)", name)
    return m.group(1) if m else name


def discover(roots: list[str] | None = None) -> list[Runtime]:
    roots = roots if roots is not None else DEFAULT_ROOTS
    found: dict[str, Runtime] = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            d = os.path.join(root, entry)
            if not os.path.isdir(d):
                continue
            launcher = _proton_launcher(d)
            if launcher:
                rt = Runtime(
                    kind=RuntimeKind.PROTON,
                    name=entry,
                    version=_guess_version(entry),
                    path=d,
                    launcher=launcher,
                )
                found.setdefault(entry, rt)
                continue
            launcher = _wine_launcher(d)
            if launcher:
                rt = Runtime(
                    kind=RuntimeKind.WINE,
                    name=entry,
                    version=_guess_version(entry),
                    path=d,
                    launcher=launcher,
                )
                found.setdefault(entry, rt)
    return list(found.values())


def find(name: str, roots: list[str] | None = None) -> Runtime | None:
    for rt in discover(roots):
        if rt.name == name:
            return rt
    return None
