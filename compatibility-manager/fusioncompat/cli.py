"""Command-line interface for the Fusion Compatibility Manager.

    fusion-compat runtimes                 list discovered Wine/Proton runtimes
    fusion-compat add <id> --title ... --exe ... --runtime ...
    fusion-compat list                     list game profiles + claimed/measured
    fusion-compat show <id>                print a profile as JSON
    fusion-compat set <id> key=value ...   edit profile fields
    fusion-compat run <id> [--real]        build+print (or run) the launch cmd
    fusion-compat doctor <id>              check a profile for problems
    fusion-compat report <id>              show the measured run history

Stdlib only. Honest by default: `run` is dry-run unless you pass --real.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import launch, report, runtimes
from .db import CompatDB, ProfileStore
from .models import CompatStatus, D3DVersion, GameProfile, GraphicsConfig, RuntimeKind
from .prefix import plan, prefix_path

# PS4 reality checks the doctor warns about.
_BLOCKED_HINTS = {
    "avx2": "needs AVX2 -- the Jaguar CPU does not have it; title will not run.",
    "eac": "kernel-level anti-cheat (EAC) typically cannot run outside Orbis.",
    "battleye": "kernel-level anti-cheat (BattlEye) typically cannot run here.",
}


def _store(args) -> ProfileStore:
    return ProfileStore(getattr(args, "root", None))


def cmd_runtimes(args) -> int:
    rts = runtimes.discover(args.roots or None)
    if not rts:
        print("No Wine/Proton runtimes found. Searched:")
        for r in (args.roots or runtimes.DEFAULT_ROOTS):
            print(f"  {r}")
        return 1
    for rt in rts:
        flag = "" if rt.maintained else "  [stale]"
        print(f"{rt.kind.value:7} {rt.name:24} {rt.version:12} {rt.path}{flag}")
    return 0


def cmd_add(args) -> int:
    store = _store(args)
    if store.exists(args.id) and not args.force:
        print(f"profile {args.id!r} exists; use --force to overwrite", file=sys.stderr)
        return 1
    profile = GameProfile(
        id=args.id,
        title=args.title or args.id,
        exe=args.exe,
        runtime=args.runtime,
        prefix=args.prefix or prefix_path(args.id),
        d3d=D3DVersion(args.d3d),
        graphics=GraphicsConfig(
            dxvk_version=args.dxvk,
            vkd3d_version=args.vkd3d,
        ),
    )
    # Seed from the shipped compat DB if we know this title.
    hit = CompatDB(args.compatdb).get(profile.title)
    if hit:
        profile.claimed_status = CompatStatus(hit["status"])
        profile.notes = f"seeded from compatdb: {hit.get('settings', {})}"
    store.save(profile)
    print(f"saved profile {profile.id} -> {store.path_for(profile.id)}")
    return 0


def cmd_list(args) -> int:
    store = _store(args)
    rows = list(store.all())
    if not rows:
        print("no profiles yet")
        return 0
    print(f"{'ID':20} {'TITLE':28} {'CLAIMED':10} {'MEASURED':10}")
    for p in rows:
        print(f"{p.id:20} {p.title[:28]:28} {p.claimed_status.value:10} "
              f"{p.measured_status.value:10}")
    return 0


def cmd_show(args) -> int:
    store = _store(args)
    if not store.exists(args.id):
        print(f"no such profile: {args.id}", file=sys.stderr)
        return 1
    print(json.dumps(store.load(args.id).to_json(), indent=2, ensure_ascii=False))
    return 0


def _coerce(profile: GameProfile, key: str, value: str) -> None:
    if key in ("title", "exe", "runtime", "prefix", "gamescope", "notes"):
        setattr(profile, key, value)
    elif key == "d3d":
        profile.d3d = D3DVersion(value)
    elif key == "dxvk":
        profile.graphics.dxvk_version = value or None
    elif key == "vkd3d":
        profile.graphics.vkd3d_version = value or None
    elif key == "dxvk_hud":
        profile.graphics.dxvk_hud = value
    elif key.startswith("override."):
        profile.dll_overrides[key.split(".", 1)[1]] = value
    elif key.startswith("env."):
        profile.env[key.split(".", 1)[1]] = value
    else:
        raise KeyError(key)


def cmd_set(args) -> int:
    store = _store(args)
    if not store.exists(args.id):
        print(f"no such profile: {args.id}", file=sys.stderr)
        return 1
    profile = store.load(args.id)
    for pair in args.pairs:
        if "=" not in pair:
            print(f"bad assignment (need key=value): {pair}", file=sys.stderr)
            return 1
        key, value = pair.split("=", 1)
        try:
            _coerce(profile, key, value)
        except KeyError:
            print(f"unknown key: {key}", file=sys.stderr)
            return 1
    store.save(profile)
    print(f"updated {profile.id}")
    return 0


def cmd_doctor(args) -> int:
    store = _store(args)
    if not store.exists(args.id):
        print(f"no such profile: {args.id}", file=sys.stderr)
        return 1
    profile = store.load(args.id)
    problems: list[str] = []
    rt = runtimes.find(profile.runtime, args.roots or None)
    if rt is None:
        problems.append(f"runtime {profile.runtime!r} not found on this system")
    hay = (profile.title + " " + profile.notes).lower()
    for needle, msg in _BLOCKED_HINTS.items():
        if needle in hay:
            problems.append(msg)
    if profile.d3d is D3DVersion.DX12 and not profile.graphics.vkd3d_version:
        problems.append("DX12 title but no VKD3D-Proton version set")
    if profile.d3d in (D3DVersion.DX9, D3DVersion.DX10, D3DVersion.DX11) \
            and not profile.graphics.dxvk_version:
        problems.append(f"{profile.d3d.value} title but no DXVK version set")
    print("Prefix setup plan:")
    for step in plan(profile, rt.kind if rt else RuntimeKind.WINE):
        print(f"  - {step}")
    if problems:
        print("\nPotential problems:")
        for p in problems:
            print(f"  ! {p}")
        return 1
    print("\nNo blocking problems detected (not a guarantee it runs).")
    return 0


def cmd_run(args) -> int:
    store = _store(args)
    if not store.exists(args.id):
        print(f"no such profile: {args.id}", file=sys.stderr)
        return 1
    profile = store.load(args.id)
    rt = runtimes.find(profile.runtime, args.roots or None)
    if rt is None:
        print(f"runtime {profile.runtime!r} not found", file=sys.stderr)
        return 1
    import time

    start = time.time()
    rc = launch.run(profile, rt, dry_run=not args.real)
    if args.real:
        report.record_run(profile.id, rc, time.time() - start)
        profile.measured_status = report.summarise(profile.id)
        store.save(profile)
        print(f"exit={rc} measured_status={profile.measured_status.value}")
    return rc


def cmd_report(args) -> int:
    runs = report.load_runs(args.id)
    if not runs:
        print("no recorded runs")
        return 0
    for r in runs:
        fps = f"{r['avg_fps']}fps" if r.get("avg_fps") else "no-fps"
        print(f"ts={r['ts']} exit={r['exit_code']} {r['seconds']}s {fps} {r.get('note','')}")
    print(f"\nmeasured status: {report.summarise(args.id).value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fusion-compat",
                                description="Fusion Compatibility Manager")
    p.add_argument("--root", help="FUSION_HOME override (profiles/prefixes live here)")
    p.add_argument("--roots", nargs="*", help="runtime search roots (testing/override)")
    p.add_argument("--compatdb", help="path to the compat database json")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("runtimes", help="list discovered runtimes").set_defaults(func=cmd_runtimes)

    a = sub.add_parser("add", help="add a game profile")
    a.add_argument("id")
    a.add_argument("--title")
    a.add_argument("--exe", required=True)
    a.add_argument("--runtime", required=True)
    a.add_argument("--prefix")
    a.add_argument("--d3d", default="unknown",
                   choices=[d.value for d in D3DVersion])
    a.add_argument("--dxvk")
    a.add_argument("--vkd3d")
    a.add_argument("--force", action="store_true")
    a.set_defaults(func=cmd_add)

    sub.add_parser("list", help="list profiles").set_defaults(func=cmd_list)

    s = sub.add_parser("show", help="print a profile")
    s.add_argument("id")
    s.set_defaults(func=cmd_show)

    st = sub.add_parser("set", help="edit profile fields (key=value ...)")
    st.add_argument("id")
    st.add_argument("pairs", nargs="+")
    st.set_defaults(func=cmd_set)

    d = sub.add_parser("doctor", help="check a profile for problems")
    d.add_argument("id")
    d.set_defaults(func=cmd_doctor)

    r = sub.add_parser("run", help="build+print (or --real run) the launch command")
    r.add_argument("id")
    r.add_argument("--real", action="store_true", help="actually launch (default: dry-run)")
    r.set_defaults(func=cmd_run)

    rp = sub.add_parser("report", help="show measured run history")
    rp.add_argument("id")
    rp.set_defaults(func=cmd_report)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
