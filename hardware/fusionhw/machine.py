"""Universal machine detection -- the brain of Fusion OS.

Detects CPU, GPU(s), RAM and storage on ANY x86-64 machine and produces:
  * a Machine description, and
  * a DriverPlan (which Vulkan ICDs / whether the NVIDIA proprietary driver is
    wanted), and
  * a TunePlan (per-disk IO scheduler, zram size, CPU pinning hint).

So Fusion OS is not tied to one box: it adapts at first boot and per launch.

Everything reads from configurable /proc and /sys roots, so it is fully
unit-testable against fake trees (see tests/). On a real system the defaults
read the live /proc and /sys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

PCI_VENDOR = {"0x10de": "nvidia", "0x1002": "amd", "0x8086": "intel"}


@dataclass
class CPU:
    vendor: str              # intel | amd | other
    model: str
    cores: int               # logical processors
    has_avx2: bool
    has_avx512: bool

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class GPU:
    vendor: str              # amd | intel | nvidia | other
    pci_id: str              # vendor:device
    is_3d_class: bool

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Disk:
    name: str
    rotational: bool         # True = spinning HDD, False = SSD/NVMe
    is_nvme: bool

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Machine:
    cpu: CPU
    gpus: list[GPU]
    mem_total_mb: int
    disks: list[Disk]

    def as_dict(self) -> dict:
        return {
            "cpu": self.cpu.as_dict(),
            "gpus": [g.as_dict() for g in self.gpus],
            "mem_total_mb": self.mem_total_mb,
            "disks": [d.as_dict() for d in self.disks],
        }


@dataclass
class DriverPlan:
    vulkan_icds: list[str] = field(default_factory=list)
    nvidia_proprietary: bool = False
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class TunePlan:
    # per-disk recommended IO scheduler
    io_scheduler: dict[str, str] = field(default_factory=dict)
    zram_mb: int = 0
    cpu_pin_hint: str = ""   # "" | "half"
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


# ---------------------------------------------------------------------
# Readers (injectable roots for testing)
# ---------------------------------------------------------------------
def read_cpu(proc_root: str = "/proc") -> CPU:
    vendor = "other"
    model = "unknown"
    flags: set[str] = set()
    count = 0
    try:
        with open(os.path.join(proc_root, "cpuinfo"), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("processor"):
                    count += 1
                elif line.startswith("vendor_id") and vendor == "other":
                    v = line.split(":", 1)[1].strip()
                    vendor = {"GenuineIntel": "intel",
                              "AuthenticAMD": "amd"}.get(v, "other")
                elif line.startswith("model name") and model == "unknown":
                    model = line.split(":", 1)[1].strip()
                elif line.startswith("flags") and not flags:
                    flags = set(line.split(":", 1)[1].split())
    except OSError:
        pass
    return CPU(vendor, model, max(count, 1),
               "avx2" in flags, "avx512f" in flags)


def read_mem_mb(proc_root: str = "/proc") -> int:
    try:
        with open(os.path.join(proc_root, "meminfo"), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError):
        pass
    return 0


def read_gpus(sys_root: str = "/sys") -> list[GPU]:
    base = os.path.join(sys_root, "bus/pci/devices")
    gpus: list[GPU] = []
    if not os.path.isdir(base):
        return gpus
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        try:
            cls = open(os.path.join(d, "class")).read().strip().lower()
            if not cls.startswith("0x03"):   # 0x03 = display controller
                continue
            vendor = open(os.path.join(d, "vendor")).read().strip().lower()
            device = open(os.path.join(d, "device")).read().strip().lower()
        except OSError:
            continue
        gpus.append(GPU(
            vendor=PCI_VENDOR.get(vendor, "other"),
            pci_id=f"{vendor.replace('0x','')}:{device.replace('0x','')}",
            is_3d_class=cls.startswith("0x0302"),
        ))
    return gpus


def read_disks(sys_root: str = "/sys") -> list[Disk]:
    base = os.path.join(sys_root, "block")
    disks: list[Disk] = []
    if not os.path.isdir(base):
        return disks
    for name in sorted(os.listdir(base)):
        if name.startswith(("loop", "ram", "zram", "sr")):
            continue
        d = os.path.join(base, name)
        try:
            rot = open(os.path.join(d, "queue/rotational")).read().strip()
        except OSError:
            continue
        disks.append(Disk(name=name, rotational=(rot == "1"),
                          is_nvme=name.startswith("nvme")))
    return disks


def detect(proc_root: str = "/proc", sys_root: str = "/sys") -> Machine:
    return Machine(
        cpu=read_cpu(proc_root),
        gpus=read_gpus(sys_root),
        mem_total_mb=read_mem_mb(proc_root),
        disks=read_disks(sys_root),
    )


# ---------------------------------------------------------------------
# Planners -- turn a Machine into driver + tuning decisions
# ---------------------------------------------------------------------
def plan_drivers(m: Machine) -> DriverPlan:
    icds: list[str] = []
    notes: list[str] = []
    nvidia = False
    vendors = {g.vendor for g in m.gpus}
    if "amd" in vendors:
        icds.append("vulkan-radeon (RADV)")
    if "intel" in vendors:
        icds.append("vulkan-intel (ANV)")
    if "nvidia" in vendors:
        nvidia = True
        icds.append("nvidia proprietary (recommended) or vulkan-nouveau (weak)")
        notes.append("NVIDIA GPU detected: the proprietary driver gives far "
                     "better gaming performance than nouveau. First-boot will "
                     "install it when online.")
    if not vendors:
        notes.append("No GPU detected via PCI class 0x03 -- check the machine.")
    return DriverPlan(vulkan_icds=icds, nvidia_proprietary=nvidia, notes=notes)


def plan_tuning(m: Machine) -> TunePlan:
    io: dict[str, str] = {}
    notes: list[str] = []
    for d in m.disks:
        if d.is_nvme:
            io[d.name] = "none"          # NVMe: let the device queue, no sched
        elif d.rotational:
            io[d.name] = "bfq"           # HDD: fairness helps interactivity
        else:
            io[d.name] = "mq-deadline"   # SATA SSD
    # zram: half of RAM, capped (more headroom on bigger machines, lean on small)
    zram = min(m.mem_total_mb // 2, 8192) if m.mem_total_mb else 0
    pin = "half" if m.cpu.cores >= 4 else ""
    if not m.cpu.has_avx2:
        notes.append("CPU lacks AVX2: some modern titles will refuse to run "
                     "(not a Fusion bug -- a hardware limit).")
    return TunePlan(io_scheduler=io, zram_mb=zram, cpu_pin_hint=pin, notes=notes)


def full_report(proc_root: str = "/proc", sys_root: str = "/sys") -> dict:
    m = detect(proc_root, sys_root)
    return {
        "machine": m.as_dict(),
        "drivers": plan_drivers(m).as_dict(),
        "tuning": plan_tuning(m).as_dict(),
    }
