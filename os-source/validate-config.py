#!/usr/bin/env python3
"""Fail if Buildroot silently dropped or changed any option we asked for.

Buildroot's Kconfig quietly discards an option whose dependencies are not met
(that is how a glibc request once turned into uClibc). This compares the LAST
value of every BR2_ option in our defconfig with the resolved .config.

    validate-config.py <our_defconfig> <output/.config> <BR2_EXTERNAL path>
"""
import re
import sys

OPT = re.compile(r"^(BR2_[A-Z0-9_]+)=(.*)$")


def read(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        m = OPT.match(line.strip())
        if m:
            out[m[1]] = m[2]          # last assignment wins, as in Kconfig
    return out


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 2
    want, have, ext = read(argv[1]), read(argv[2]), argv[3]
    bad = []
    for key, val in want.items():
        expanded = val.replace("$(BR2_EXTERNAL_FUSION_PATH)", ext)
        if have.get(key) not in (val, expanded):
            bad.append((key, val, have.get(key, "<not set>")))
    if bad:
        print("Buildroot dropped/changed requested options:")
        for key, val, got in bad:
            print(f"  {key}: wanted {val}, got {got}")
        print("Fix the missing dependency (see the option's Config.in).")
        return 1
    print(f"config OK: all {len(want)} requested options survived")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
