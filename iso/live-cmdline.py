#!/usr/bin/env python3
"""Give the Arch live ISO's boot entries the Fusion performance cmdline.

    live-cmdline.py <archiso profile dir> <fusion-cmdline.conf>

archiso keeps its boot menus in the profile, not in airootfs, so
fusion-perf-baseline.sh cannot see them ("no known bootloader config found").
This edits them directly:

  * the main entries (systemd-boot for UEFI, syslinux for BIOS) get the
    Fusion parameters;
  * a "safe" copy of each main entry is added WITHOUT them (CPU mitigations
    on, watchdogs and power saving at kernel defaults), in case a machine
    misbehaves with them.

Accessibility (speech) entries are left alone.
"""
import pathlib
import re
import sys

MARK = "archisobasedir="


def params(conf):
    out = []
    for line in pathlib.Path(conf).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            out.extend(line.split())
    return out


def add(line, extra):
    have = set(line.split())
    return line.rstrip() + "".join(f" {p}" for p in extra if p not in have)


def systemd_boot(profile, extra):
    done = 0
    for entry in sorted((profile / "efiboot" / "loader" / "entries").glob("*.conf")):
        text = entry.read_text()
        if "accessibility" in text or "-safe" in entry.stem or MARK not in text:
            continue
        safe = entry.with_name(entry.stem + "-safe.conf")
        safe.write_text(re.sub(r"^(title\s+.*)$", r"\1 (safe)", text, count=1, flags=re.M))
        entry.write_text("\n".join(add(l, extra) if l.startswith("options") else l
                                   for l in text.splitlines()) + "\n")
        done += 1
    return done


def syslinux(profile, extra):
    done = 0
    for cfg in sorted((profile / "syslinux").glob("archiso_sys*.cfg")):
        lines = cfg.read_text().splitlines()
        # Split into LABEL blocks; keep the header before the first LABEL.
        blocks, cur = [], []
        for l in lines:
            if l.strip().upper().startswith("LABEL ") and cur:
                blocks.append(cur)
                cur = []
            cur.append(l)
        blocks.append(cur)
        out = []
        for b in blocks:
            is_entry = b and b[0].strip().upper().startswith("LABEL ")
            text = "\n".join(b)
            if not is_entry or MARK not in text or "accessibility" in text:
                out.extend(b)
                continue
            # Trailing blank/comment lines belong to the next entry.
            tail = []
            while b and (not b[-1].strip() or b[-1].lstrip().startswith("#")):
                tail.insert(0, b.pop())
            out.extend(add(l, extra) if l.strip().upper().startswith("APPEND") else l for l in b)
            safe = [""]
            for l in b:
                s = l.strip().upper()
                if s.startswith("LABEL "):
                    l = l.rstrip() + "safe"
                elif s.startswith("MENU LABEL"):
                    l = l.rstrip() + " (safe)"
                elif s.startswith("MENU DEFAULT") or s.startswith("#"):
                    continue
                safe.append(l)
            out.extend(safe)
            out.extend(tail)
            done += 1
        cfg.write_text("\n".join(out) + "\n")
    return done


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    profile, extra = pathlib.Path(argv[1]), params(argv[2])
    n_uefi, n_bios = systemd_boot(profile, extra), syslinux(profile, extra)
    print(f"live-cmdline: {n_uefi} UEFI and {n_bios} BIOS entries got: {' '.join(extra)}")
    if n_uefi == 0 or n_bios == 0:
        print("live-cmdline: expected at least one UEFI and one BIOS entry", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
