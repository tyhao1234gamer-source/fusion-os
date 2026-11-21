"""Fusion Performance Engine (fusionopt).

Reversible, inspectable system tuning for PS4 Fusion OS. Four profiles
(EXTREME / COMPETITIVE / BALANCED / LOW_RESOURCE), applied through a Backend so
the same code dry-runs anywhere and runs for real on target. Snapshots every
knob before changing it; `restore` puts them all back.

No overclocking, undervolting or fan-curve changes -- out of scope by design.
Performance claims belong to the Benchmark, not here.
"""

__version__ = "0.1.0"
__all__ = ["backend", "profiles", "engine"]
