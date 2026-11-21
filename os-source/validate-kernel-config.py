#!/usr/bin/env python3
"""Report kernel options from our fragments that the kernel's Kconfig dropped.

The kernel, like Buildroot, silently drops an option whose dependencies are
not met. This compares every CONFIG_ line of the given fragments with the
final kernel .config of the build.

    validate-kernel-config.py <kernel .config> <fragment> [<fragment> ...]

Exit 1 when something was dropped or changed. "=m" satisfied by "=y" is
accepted (built-in is a superset of a module).
"""
import re
import sys

OPT = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")


def read(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        m = OPT.match(line)
        if m:
            out[m[1]] = m[2]
            continue
        m = UNSET.match(line)
        if m:
            out[m[1]] = "n"
    return out


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    have = read(argv[1])
    want = {}
    for frag in argv[2:]:
        want.update(read(frag))          # later fragments win, like the merge
    bad = []
    for key, val in sorted(want.items()):
        got = have.get(key, "n")
        if got == val or (val == "m" and got == "y"):
            continue
        bad.append((key, val, got))
    if bad:
        print(f"Kernel dropped/changed {len(bad)} of {len(want)} requested options:")
        for key, val, got in bad:
            print(f"  {key}: wanted {val}, got {got}")
        return 1
    print(f"kernel config OK: all {len(want)} requested options present")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
