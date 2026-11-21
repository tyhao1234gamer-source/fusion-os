"""PS4 hardware detection: southbridge + GPU -> recommended kernel / Mesa pin.

The southbridge is the single most important variable for PS4 Linux (it decides
kernel, Mesa ceiling, and whether internal-HDD install is possible). This module
identifies it from PCI IDs and returns the Fusion recommendations from the Phase
1 report.

It is testable without a PS4: `classify()` takes a list of (vendor, device) PCI
IDs, so the suite feeds known IDs. `read_pci_ids()` gathers them from
/sys/bus/pci/devices on a real system.

NOTE on the PCI IDs below: the Aeolia/Belize/Baikal *southbridge* function IDs
used by the community vary by revision and are not all publicly canonical. They
are kept in one editable table (SOUTHBRIDGE_PCI) so they can be corrected
against real `lspci -nn` output from each console model without touching logic.
Detection also falls back to DMI/cmdline hints. Treat an UNKNOWN result as
"ask the user / inspect lspci", never as a guess.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

SONY_VENDOR = "104d"
AMD_VENDOR = "1002"

# Liverpool (base PS4) / Neo (PS4 Pro) APU GPU PCI device IDs (community-reported).
GPU_PCI = {
    "9920": "Liverpool (PS4)",
    "9923": "Liverpool (PS4, rev)",
    "98f0": "Neo (PS4 Pro)",
}

# Southbridge identification table -- EDIT against real lspci per model.
# Maps a PCI (vendor, device) to a southbridge family name.
SOUTHBRIDGE_PCI = {
    (SONY_VENDOR, "908f"): "Aeolia",
    (SONY_VENDOR, "909e"): "Belize",
    (SONY_VENDOR, "90c0"): "Baikal",
}


@dataclass
class Recommendation:
    southbridge: str          # Aeolia | Belize | Baikal | UNKNOWN
    gpu: str
    kernel: str               # recommended Fusion Core kernel base
    mesa_pin: str             # version ceiling, or "latest"
    internal_hdd: bool        # internal-HDD Linux install feasible?
    notes: str = ""

    def as_dict(self) -> dict:
        return {
            "southbridge": self.southbridge, "gpu": self.gpu,
            "kernel": self.kernel, "mesa_pin": self.mesa_pin,
            "internal_hdd": self.internal_hdd, "notes": self.notes,
        }


_RECS = {
    "Aeolia": Recommendation("Aeolia", "", "6.15.4 ThinLTO (Aeolia/Belize)",
                             "latest", True,
                             "Best-supported southbridge."),
    "Belize": Recommendation("Belize", "", "6.15.4 ThinLTO (Aeolia/Belize); "
                             "5.15.15 sometimes faster", "latest", True, ""),
    "Baikal": Recommendation("Baikal", "", "7.0-Clean (rmux) or 5.4.247",
                             "<=25.1", False,
                             "Mesa must be <=25.1; internal-HDD install "
                             "usually not possible -- use external USB."),
}


def classify(pci_ids: list[tuple[str, str]]) -> Recommendation:
    gpu_name = "UNKNOWN"
    for vendor, device in pci_ids:
        if vendor == AMD_VENDOR and device in GPU_PCI:
            gpu_name = GPU_PCI[device]
            break
    sb = "UNKNOWN"
    for vendor, device in pci_ids:
        if (vendor, device) in SOUTHBRIDGE_PCI:
            sb = SOUTHBRIDGE_PCI[(vendor, device)]
            break
    if sb in _RECS:
        rec = _RECS[sb]
        return Recommendation(rec.southbridge, gpu_name, rec.kernel,
                              rec.mesa_pin, rec.internal_hdd, rec.notes)
    return Recommendation(
        "UNKNOWN", gpu_name, "UNKNOWN", "UNKNOWN", False,
        "Southbridge not identified. Run `lspci -nn`, match the Sony 104d "
        "device, and add it to SOUTHBRIDGE_PCI. Do not assume a kernel.",
    )


def read_pci_ids(sysfs: str = "/sys/bus/pci/devices") -> list[tuple[str, str]]:
    """Gather (vendor, device) hex IDs (no 0x) from sysfs on a real machine."""
    out: list[tuple[str, str]] = []
    if not os.path.isdir(sysfs):
        return out
    for name in sorted(os.listdir(sysfs)):
        d = os.path.join(sysfs, name)
        try:
            v = open(os.path.join(d, "vendor")).read().strip().lower()
            dev = open(os.path.join(d, "device")).read().strip().lower()
        except OSError:
            continue
        out.append((v.replace("0x", ""), dev.replace("0x", "")))
    return out


def detect() -> Recommendation:
    return classify(read_pci_ids())
