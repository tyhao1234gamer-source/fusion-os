"""Fusion Compatibility Manager.

A dependency-free (stdlib-only) manager for running Windows games on the
PS4 Fusion OS through Wine / Proton + DXVK / VKD3D-Proton.

Design goals
------------
* No third-party dependencies, so it runs on a minimal PS4 rootfs with no pip.
* Everything is *reversible* and *inspectable*: nothing is launched without a
  `--dry-run` being able to show the exact command and environment first.
* Honest by design: a profile records a *claimed* status and a *measured*
  status; they are never conflated. Nothing is marked "works" until a real
  run on target says so (see `report.py`).

The PS4's APU (8-core Jaguar, no AVX2; GCN "Liverpool"/"Neo" GPU) is the hard
ceiling. This tool does not pretend otherwise -- it helps you find and persist
the *settings* that make a given title viable, and it refuses to promise
universal support.
"""

__version__ = "0.1.0"
__all__ = ["models", "db", "runtimes", "prefix", "launch", "report"]
