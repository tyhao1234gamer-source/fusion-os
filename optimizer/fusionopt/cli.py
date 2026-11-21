"""CLI for the Fusion Performance Engine.

    fusion-opt list                      show the four profiles
    fusion-opt plan <profile>            show exactly what would change
    fusion-opt apply <profile> [--real]  apply (dry-run unless --real)
    fusion-opt status                    show the active profile
    fusion-opt restore [--real]          revert to pre-profile state

Dry-run by default. --real requires write access to /sys and /proc (root).
"""

from __future__ import annotations

import argparse
import json
import os

from .backend import DryRunBackend, SysfsBackend
from .engine import Engine
from .profiles import PROFILES, resolve


def _backend(real: bool) -> object:
    if real:
        return SysfsBackend()
    # Seed a dry-run backend with plausible current values so plans read well.
    seed = {}
    for i in range(8):  # 8 Jaguar cores
        seed[f"/sys/devices/system/cpu/cpu{i}/cpufreq/scaling_governor"] = "schedutil"
    seed["/proc/sys/vm/swappiness"] = "60"
    seed["/proc/sys/vm/dirty_ratio"] = "20"
    seed["/proc/sys/vm/dirty_background_ratio"] = "10"
    seed["/sys/kernel/mm/transparent_hugepage/enabled"] = "always [madvise] never"
    seed["/sys/block/sda/queue/scheduler"] = "[mq-deadline] none"
    seed["/sys/block/sda/queue/nr_requests"] = "64"
    seed["/proc/sys/kernel/sched_migration_cost_ns"] = "500000"
    seed["/proc/sys/vm/compaction_proactiveness"] = "20"
    return DryRunBackend(seed)


def cmd_list(args) -> int:
    for key, p in PROFILES.items():
        print(f"{key:12} {p.name}")
        print(f"             {p.summary}")
        if p.game_cpuset:
            print(f"             game pinned to CPUs {p.game_cpuset}")
        print()
    return 0


def cmd_plan(args) -> int:
    eng = Engine(_backend(False), args.root)
    try:
        profile = resolve(args.profile)
    except KeyError:
        print(f"unknown profile: {args.profile}")
        return 1
    for a in eng.plan(profile):
        if a.get("key") == "service":
            print(f"service {a['action']:6} {a['name']}")
        elif a["status"] == "absent":
            print(f"absent  {a['path']}")
        elif a["status"] == "noop":
            print(f"noop    {a['path']} (already {a['to']})")
        else:
            print(f"change  {a['path']}: {a['from']} -> {a['to']}")
    return 0


def cmd_apply(args) -> int:
    eng = Engine(_backend(args.real), args.root)
    try:
        profile = resolve(args.profile)
    except KeyError:
        print(f"unknown profile: {args.profile}")
        return 1
    if args.real and os.geteuid() != 0:
        print("--real needs root (writing to /sys and /proc). Re-run with sudo.")
        return 2
    res = eng.apply(profile)
    print(json.dumps(res, indent=2))
    if profile.game_cpuset:
        print(f"\nHint: launch games pinned to CPUs {profile.game_cpuset} "
              f"(export FUSION_GAME_CPUSET={profile.game_cpuset})")
    if not args.real:
        print("\n(dry-run: nothing was written; pass --real to apply)")
    return 0


def cmd_status(args) -> int:
    eng = Engine(_backend(args.real if hasattr(args, "real") else False), args.root)
    active = eng.active()
    if not active:
        print("no Fusion profile active (system defaults)")
        return 0
    print(f"active profile: {active['profile']}")
    print(f"reversible knobs recorded: {len(active.get('snapshot', {}))}")
    if active.get("game_cpuset"):
        print(f"game cpuset: {active['game_cpuset']}")
    return 0


def cmd_restore(args) -> int:
    eng = Engine(_backend(args.real), args.root)
    if args.real and os.geteuid() != 0:
        print("--real needs root. Re-run with sudo.")
        return 2
    print(json.dumps(eng.restore(), indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fusion-opt",
                                description="Fusion Performance Engine")
    p.add_argument("--root", help="FUSION_HOME override (state file location)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list").set_defaults(func=cmd_list)

    pl = sub.add_parser("plan"); pl.add_argument("profile"); pl.set_defaults(func=cmd_plan)

    ap = sub.add_parser("apply"); ap.add_argument("profile")
    ap.add_argument("--real", action="store_true"); ap.set_defaults(func=cmd_apply)

    stt = sub.add_parser("status"); stt.add_argument("--real", action="store_true")
    stt.set_defaults(func=cmd_status)

    rs = sub.add_parser("restore"); rs.add_argument("--real", action="store_true")
    rs.set_defaults(func=cmd_restore)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
