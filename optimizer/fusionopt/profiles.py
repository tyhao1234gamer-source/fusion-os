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
    # Hint consumed by the launcher: which CPUs to pin the game to.
    # "" = all cores; "half" = the first half of online cores (resolved at
    # launch by resolve_cpuset), so background/driver threads stay off the
    # cores the game runs on. A literal mask like "0-3" is also accepted.
    game_cpuset: str = ""


# Non-gaming services that are safe to stop while gaming on a single-user PC.
# bluetooth.service is NOT here: wireless controllers (DualSense, Xbox,
# Switch Pro) and headsets need it, and an idle bluetoothd costs ~nothing.
_HEAVY_SERVICES = [
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
IO_SCHED_NVME = "/sys/block/nvme*/queue/scheduler"
NR_REQUESTS = "/sys/block/sd*/queue/nr_requests"
SCHED_MIGRATION = "/proc/sys/kernel/sched_migration_cost_ns"
SPLIT_LOCK = "/sys/kernel/debug/x86/split_lock_detect"
# GPU power/performance (generic laptop GPUs; absent knobs are skipped safely):
#   AMD (amdgpu): auto | low | high | manual
AMDGPU_DPM = "/sys/class/drm/card*/device/power_dpm_force_performance_level"
#   Intel (i915) RPS max frequency boost flag
INTEL_BOOST = "/sys/class/drm/card*/gt_boost_freq_mhz"
# EPP (energy_performance_preference) on intel_pstate/amd-pstate active mode.
EPP = "/sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference"


def _gov(value: str) -> Tunable:
    return Tunable("cpu_governor", CPU_GOV, value, f"CPU governor -> {value}")


PROFILES: dict[str, Profile] = {
    "extreme": Profile(
        name="EXTREME PERFORMANCE",
        summary="Sustained max throughput. performance governor, GPU forced high, "
                "low swappiness, deadline IO, THP on. No clocks/voltages/fan touched.",
        tunables=[
            _gov("performance"),
            Tunable("epp", EPP, "performance", "energy-perf pref -> performance"),
            Tunable("gpu_dpm", AMDGPU_DPM, "high", "amdgpu: hold max perf level"),
            Tunable("swappiness", SWAPPINESS, "10"),
            Tunable("dirty_ratio", DIRTY_RATIO, "10"),
            Tunable("dirty_bg_ratio", DIRTY_BG, "5"),
            Tunable("thp", THP, "madvise", "transparent hugepages on-demand"),
            Tunable("io_scheduler", IO_SCHED, "mq-deadline"),
            Tunable("io_scheduler_nvme", IO_SCHED_NVME, "none", "NVMe: no IO sched"),
            Tunable("nr_requests", NR_REQUESTS, "256"),
            Tunable("sched_migration_cost", SCHED_MIGRATION, "5000000",
                    "reduce needless task migration"),
        ],
        services=_HEAVY_SERVICES,
        game_cpuset="",   # all cores available to the game
    ),
    "competitive": Profile(
        name="COMPETITIVE GAMING",
        summary="Lowest latency. performance governor, GPU forced high, game pinned "
                "to the first half of cores so background work stays off them.",
        tunables=[
            _gov("performance"),
            Tunable("epp", EPP, "performance"),
            Tunable("gpu_dpm", AMDGPU_DPM, "high"),
            Tunable("swappiness", SWAPPINESS, "1"),
            Tunable("sched_migration_cost", SCHED_MIGRATION, "5000000"),
            Tunable("compaction", COMPACTION, "0", "no background compaction jitter"),
            Tunable("io_scheduler", IO_SCHED, "mq-deadline"),
            Tunable("io_scheduler_nvme", IO_SCHED_NVME, "none"),
            Tunable("split_lock", SPLIT_LOCK, "0", "don't stall on split locks"),
        ],
        services=_HEAVY_SERVICES,
        game_cpuset="half",   # resolved at launch to the first half of online CPUs
    ),
    "balanced": Profile(
        name="BALANCED GAMING",
        summary="Sensible default. schedutil governor, GPU auto, zram-friendly "
                "swappiness, deadline IO.",
        tunables=[
            _gov("schedutil"),
            Tunable("gpu_dpm", AMDGPU_DPM, "auto"),
            Tunable("swappiness", SWAPPINESS, "100", "lean on zram, spare the disk"),
            Tunable("dirty_ratio", DIRTY_RATIO, "20"),
            Tunable("io_scheduler", IO_SCHED, "mq-deadline"),
        ],
        services=[],
        game_cpuset="",
    ),
    "low": Profile(
        name="LOW RESOURCE MODE",
        summary="Minimal footprint for light/2D games and emulation. powersave "
                "governor, GPU low, high swappiness to free RAM.",
        tunables=[
            _gov("powersave"),
            Tunable("gpu_dpm", AMDGPU_DPM, "low"),
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


def resolve_cpuset(token: str, cpu_count: int | None = None) -> str:
    """Turn a game_cpuset hint into a concrete taskset mask for this machine.

    "" -> "" (no pinning). "half" -> first half of online cores. A literal
    mask ("0-3", "2,4") is returned unchanged. Degrades sensibly on 1-2 core
    laptops (never pins to zero cores).
    """
    import os

    if not token:
        return ""
    if token != "half":
        return token
    n = cpu_count or os.cpu_count() or 1
    if n <= 2:
        return ""  # too few cores to carve up; let the scheduler decide
    half = max(1, n // 2)
    return f"0-{half - 1}"
