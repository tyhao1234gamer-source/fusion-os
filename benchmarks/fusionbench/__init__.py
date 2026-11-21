"""Fusion Benchmark (fusionbench).

Reproducible measurement of idle RAM/CPU, boot time, and per-game frame data
(avg FPS, 1% low, frametime percentiles), compared against saved baselines.
The project's honesty rule lives here: a gain is only real if it shows up as a
delta against a reference run, computed the same way every time.
"""

__version__ = "0.1.0"
__all__ = ["metrics", "record"]
