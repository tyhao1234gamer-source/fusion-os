"""Fusion hardware detection (fusionhw).

Identifies the PS4 southbridge (Aeolia / Belize / Baikal) and GPU from PCI IDs
and returns the Fusion kernel + Mesa-pin recommendation. UNKNOWN is a valid,
honest result -- the installer asks rather than guessing.
"""

__version__ = "0.1.0"
__all__ = ["detect"]
