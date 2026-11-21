"""Fusion first-run setup wizard (fusionsetup).

A boot-time screen to pick region, timezone, keyboard and network (Wi-Fi or
Ethernet). No account creation, no cloud/Steam sign-in -- Fusion auto-logs in a
local session. Flow logic is backend- and prompt-injected, so it is fully
unit-testable.
"""

__version__ = "0.1.0"
__all__ = ["backend", "wizard"]
