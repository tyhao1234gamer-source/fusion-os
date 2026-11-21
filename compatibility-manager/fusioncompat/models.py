"""Data models for the Fusion Compatibility Manager.

Plain dataclasses with explicit JSON (de)serialization so the on-disk format
is stable and human-editable. No external schema library -- stdlib only.
"""

from __future__ import annotations

import dataclasses
import enum
from dataclasses import dataclass, field
from typing import Any


class RuntimeKind(str, enum.Enum):
    WINE = "wine"
    PROTON = "proton"


class CompatStatus(str, enum.Enum):
    """How well a title is known to run on PS4 hardware.

    UNKNOWN   -- never run / no data yet (the honest default).
    PLAYABLE  -- runs at an acceptable, measured frame rate.
    RUNNABLE  -- boots and is playable with caveats (low FPS, glitches).
    MENU_ONLY -- launches but not actually playable.
    BROKEN    -- does not start, or crashes immediately.
    BLOCKED   -- cannot work on this hardware (needs AVX2, kernel anti-cheat,
                 GPU feature the Liverpool/Neo lacks). Not a bug to chase.
    """

    UNKNOWN = "unknown"
    PLAYABLE = "playable"
    RUNNABLE = "runnable"
    MENU_ONLY = "menu_only"
    BROKEN = "broken"
    BLOCKED = "blocked"


class D3DVersion(str, enum.Enum):
    DX8 = "dx8"
    DX9 = "dx9"
    DX10 = "dx10"
    DX11 = "dx11"
    DX12 = "dx12"
    VULKAN = "vulkan"
    OPENGL = "opengl"
    UNKNOWN = "unknown"


@dataclass
class Runtime:
    """A discovered Wine or Proton runtime on disk."""

    kind: RuntimeKind
    name: str                 # e.g. "wine-ge-8-26" or "proton-9.0"
    version: str              # e.g. "8.26"
    path: str                 # root directory of the runtime
    launcher: str             # wine binary, or proton entry script
    maintained: bool = True   # False => flagged as stale/unmaintained

    def to_json(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["kind"] = self.kind.value
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "Runtime":
        return cls(
            kind=RuntimeKind(d["kind"]),
            name=d["name"],
            version=d["version"],
            path=d["path"],
            launcher=d["launcher"],
            maintained=d.get("maintained", True),
        )


@dataclass
class GraphicsConfig:
    """Translation-layer configuration for a title."""

    dxvk_version: str | None = None       # None => use runtime default / disabled
    vkd3d_version: str | None = None
    d8vk: bool = False
    dxvk_async: bool = False              # only meaningful on async-capable builds
    dxvk_hud: str = ""                    # e.g. "fps,frametimes"
    # Shader caching is the single biggest stutter win on the Jaguar; on by default.
    shader_cache: bool = True

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "GraphicsConfig":
        return cls(**{k: d[k] for k in d if k in cls.__dataclass_fields__})


@dataclass
class GameProfile:
    """Everything needed to launch and reproduce one Windows title."""

    id: str                               # slug, unique
    title: str
    exe: str                              # absolute path to the .exe inside prefix
    runtime: str                          # Runtime.name to use
    prefix: str                           # WINEPREFIX / proton compat data path
    d3d: D3DVersion = D3DVersion.UNKNOWN
    graphics: GraphicsConfig = field(default_factory=GraphicsConfig)
    dll_overrides: dict[str, str] = field(default_factory=dict)  # {"dinput8": "n,b"}
    env: dict[str, str] = field(default_factory=dict)            # extra env vars
    args: list[str] = field(default_factory=list)                # args passed to exe
    gamescope: str = ""                   # gamescope arg string, "" => disabled
    # Claimed vs measured -- never merge these two.
    claimed_status: CompatStatus = CompatStatus.UNKNOWN
    measured_status: CompatStatus = CompatStatus.UNKNOWN
    notes: str = ""

    def to_json(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        d["d3d"] = self.d3d.value
        d["graphics"] = self.graphics.to_json()
        d["claimed_status"] = self.claimed_status.value
        d["measured_status"] = self.measured_status.value
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "GameProfile":
        return cls(
            id=d["id"],
            title=d["title"],
            exe=d["exe"],
            runtime=d["runtime"],
            prefix=d["prefix"],
            d3d=D3DVersion(d.get("d3d", "unknown")),
            graphics=GraphicsConfig.from_json(d.get("graphics", {})),
            dll_overrides=dict(d.get("dll_overrides", {})),
            env=dict(d.get("env", {})),
            args=list(d.get("args", [])),
            gamescope=d.get("gamescope", ""),
            claimed_status=CompatStatus(d.get("claimed_status", "unknown")),
            measured_status=CompatStatus(d.get("measured_status", "unknown")),
            notes=d.get("notes", ""),
        )
