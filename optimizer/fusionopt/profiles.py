"""The Fusion performance profiles.

Four modes, as the directive asks:

    EXTREME      -- sustained maximum performance (no thermal/electrical limits
                    touched; purely scheduler/governor/memory/IO policy).
    COMPETITIVE  -- lowest latency: performance governor, no compositor-induced
                    lag, aggressive timer/IO, game pinned to one Jaguar cluster.
    BALANCED     -- the sane default: schedutil, moderate swappiness, zram on.
    LOW_RESOURCE -- minimal RAM/CPU footprint for light games and emulation.

A profile is a declarative bag of tunables. Each Tunable is one sysfs/proc
write (possibly glob-expanded across CPUs) or a service action. The engine
snapshots the current value of every path a profile touches *before* writing,
so any profile can be fully reversed.

Paths are the standard Linux locations; on hardware that lacks a given knob the
backend read returns None and the engine skips it (recorded as "absent").
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Tunable:
    key: str                 # stable identifier
    path: str                # sysfs/proc path, may contain a glob
    value: str               # value to write
    note: str = ""


@dataclass(frozen=True)
class ServiceAction:
    action: str              # 'stop' | 'start' | 'mask' | 'unmask'
    name: str


@dataclass(frozen=True)
class Profile:
    name: str
    summary: str
    tunables: list[Tunable] = field(default_factory=list)
    services: list[ServiceAction] = field(default_factory=list)
    # Hint consumed by the Gaming Shell / Compatibility Manager when launching:
    # which CPUs to pin the game to. The base PS4 is 8 Jaguar cores in two
    # 4-core clusters (0-3, 4-7); pinning a game to one cluster keeps the other
    # free for Wine/Proton/driver threads and reduces cross-cluster latency.
    game_cpuset: str = ""


# Non-gaming services that are safe to stop while gaming on a single-user PS4.
_HEAVY_SERVICES = [
    ServiceAction("stop", "bluetooth.service"),
    ServiceAction("stop", "cups.service"),
    ServiceAction("stop", "ModemManager.service"),
    ServiceAction("stop", "systemd-timesyncd.service"),
]

CPU_GOV = "/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor"
SWAPPINESS = "/proc/sys/vm/swappiness"
DIRTY_RATIO = "/proc/sys/vm/dirty_ratio"
DIRTY_BG = "/proc/sys/vm/dirty_background_ratio"
COMPACTION = "/proc/sys/vm/compaction_proactiveness"
THP = "/sys/kernel/mm/transparent_hugepage/enabled"
IO_SCHED = "/sys/block/sd*/queue/scheduler"
NR_REQUESTS = "/sys/block/sd*/queue/nr_requests"
SCHED_MIGRATION = "/proc/sys/kernel/sched_migration_cost_ns"
SPLIT_LOCK = "/sys/kernel/debug/x86/split_lock_detect"


def _gov(value: str) -> Tunable:
    return Tunable("cpu_governor", CPU_GOV, value, f"CPU governor -> {value}")


PROFILES: dict[str, Profile] = {
    "extreme": Profile(
        name="EXTREME PERFORMANCE",
        summary="Sustained max throughput. Performance governor, low swappiness, "
                "mq-deadline IO, THP on. No clocks/voltages/fan touched.",
        tunables=[
            _gov("performance"),
            Tunable("swappiness", SWAPPINESS, "10"),
            Tunable("dirty_ratio", DIRTY_RATIO, "10"),
            Tunable("dirty_bg_ratio", DIRTY_BG, "5"),
            Tunable("thp", THP, "madvise", "transparent hugepages on-demand"),
            Tunable("io_scheduler", IO_SCHED, "mq-deadline"),
            Tunable("nr_requests", NR_REQUESTS, "256"),
            Tunable("sched_migration_cost", SCHED_MIGRATION, "5000000",
                    "reduce needless task migration between Jaguar clusters"),
        ],
        services=_HEAVY_SERVICES,
        game_cpuset="",   # all 8 cores available to the game
    ),
    "competitive": Profile(
        name="COMPETITIVE GAMING",
        summary="Lowest latency. Performance governor, game pinned to cluster 0 "
                "(cores 0-3), background work pushed to cluster 1.",
        tunables=[
            _gov("performance"),
            Tunable("swappiness", SWAPPINESS, "1"),
            Tunable("sched_migration_cost", SCHED_MIGRATION, "5000000"),
            Tunable("compaction", COMPACTION, "0", "no background compaction jitter"),
            Tunable("io_scheduler", IO_SCHED, "mq-deadline"),
            Tunable("split_lock", SPLIT_LOCK, "0", "don't stall on split locks"),
        ],
        services=_HEAVY_SERVICES,
        game_cpuset="0-3",
    ),
    "balanced": Profile(
        name="BALANCED GAMING",
        summary="Sensible default. schedutil governor, zram-friendly swappiness, "
                "mq-deadline IO.",
        tunables=[
            _gov("schedutil"),
            Tunable("swappiness", SWAPPINESS, "100", "lean on zram, spare the HDD"),
            Tunable("dirty_ratio", DIRTY_RATIO, "20"),
            Tunable("io_scheduler", IO_SCHED, "mq-deadline"),
        ],
        services=[ServiceAction("stop", "bluetooth.service")],
        game_cpuset="",
    ),
    "low": Profile(
        name="LOW RESOURCE MODE",
        summary="Minimal footprint for light/2D games and emulation. powersave "
                "governor, high swappiness to free RAM.",
        tunables=[
            _gov("powersave"),
            Tunable("swappiness", SWAPPINESS, "120"),
            Tunable("thp", THP, "never", "save RAM; avoid hugepage bookkeeping"),
            Tunable("io_scheduler", IO_SCHED, "none"),
        ],
        services=_HEAVY_SERVICES,
        game_cpuset="",
    ),
}

ALIASES = {
    "extreme performance": "extreme",
    "competitive gaming": "competitive",
    "balanced gaming": "balanced",
    "low resource mode": "low",
    "max": "extreme",
}


def resolve(name: str) -> Profile:
    key = name.strip().lower()
    key = ALIASES.get(key, key)
    if key not in PROFILES:
        raise KeyError(name)
    return PROFILES[key]
