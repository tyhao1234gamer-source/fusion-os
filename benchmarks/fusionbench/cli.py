"""CLI for the Fusion Benchmark.

    fusion-bench idle [--save NAME]        measure idle RAM/CPU/boot (optionally baseline)
    fusion-bench frames FILE [--save NAME] compute FPS/1%-low from a frametime log
    fusion-bench baselines                 list saved baselines
    fusion-bench compare NAME FILE         compare a frametime log vs a saved baseline
"""

from __future__ import annotations

import argparse
import json

from . import metrics
from .record import BaselineStore, compare, fps_stats_from_frametimes, read_frametimes


def cmd_idle(args) -> int:
    snap = metrics.snapshot(args.sample)
    print(json.dumps(snap, indent=2))
    if args.save:
        BaselineStore(args.store).set(args.save, snap)
        print(f"saved baseline '{args.save}'")
    return 0


def cmd_frames(args) -> int:
    ft = read_frametimes(args.file)
    stats = fps_stats_from_frametimes(ft)
    print(json.dumps(stats, indent=2))
    if args.save:
        BaselineStore(args.store).set(args.save, stats)
        print(f"saved baseline '{args.save}'")
    return 0


def cmd_baselines(args) -> int:
    store = BaselineStore(args.store)
    names = store.names()
    if not names:
        print("no baselines saved")
        return 0
    for n in names:
        rec = store.get(n)
        keys = {k: v for k, v in rec.items() if k in
                ("avg_fps", "one_pct_low_fps", "mem_used_mb", "boot_s")}
        print(f"{n:24} {keys}")
    return 0


def cmd_compare(args) -> int:
    store = BaselineStore(args.store)
    base = store.get(args.name)
    if base is None:
        print(f"no such baseline: {args.name}")
        return 1
    cur = fps_stats_from_frametimes(read_frametimes(args.file))
    report = compare(base, cur)
    for k, d in report.items():
        arrow = "=" if d["better"] is None else ("↑" if d["better"] else "↓")
        verdict = "same" if d["better"] is None else ("better" if d["better"] else "worse")
        print(f"{k:20} {d['baseline']} -> {d['current']}  (Δ{d['delta']}) {arrow} {verdict}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fusion-bench", description="Fusion Benchmark")
    p.add_argument("--store", help="baselines.json path override")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("idle"); i.add_argument("--sample", type=float, default=1.0)
    i.add_argument("--save"); i.set_defaults(func=cmd_idle)

    f = sub.add_parser("frames"); f.add_argument("file")
    f.add_argument("--save"); f.set_defaults(func=cmd_frames)

    sub.add_parser("baselines").set_defaults(func=cmd_baselines)

    c = sub.add_parser("compare"); c.add_argument("name"); c.add_argument("file")
    c.set_defaults(func=cmd_compare)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
