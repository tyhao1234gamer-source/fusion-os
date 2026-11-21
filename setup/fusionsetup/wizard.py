"""The first-run setup flow. Region, timezone, keyboard, network. No account.

`run_wizard(backend, ask)` is the whole flow. `ask` is an injected function so
the flow is testable without a terminal:

    ask(prompt, options=None, default=None, password=False) -> str

In production `ask` is a TTY menu prompter (cli.py); in tests it is a scripted
function. The flow never creates a user, never asks for a Steam/cloud login.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .backend import SetupBackend

# A short, friendly shortlist so the user isn't scrolling 400 timezones; they
# can always type a full "Area/City" that the backend validates.
COMMON_TZ = [
    "Europe/Lisbon", "Europe/Madrid", "Europe/London", "Europe/Paris",
    "Europe/Berlin", "America/New_York", "America/Sao_Paulo", "UTC",
]
COMMON_KEYMAPS = ["pt-latin1", "pt", "es", "us", "uk", "fr", "de", "br-abnt2"]
COMMON_LOCALES = ["pt_PT.UTF-8", "pt_BR.UTF-8", "es_ES.UTF-8", "en_US.UTF-8",
                  "en_GB.UTF-8", "fr_FR.UTF-8", "de_DE.UTF-8"]


@dataclass
class SetupResult:
    locale: str = ""
    timezone: str = ""
    keymap: str = ""
    network: str = ""      # "ethernet" | "wifi:<ssid>" | "skipped"
    applied: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def _choose(ask, prompt, options, default=None):
    """Offer a shortlist; accept a typed value not in the list too."""
    return ask(prompt, options=options, default=default)


def run_wizard(backend: SetupBackend, ask) -> SetupResult:
    r = SetupResult()

    # --- 1. Region / locale ---
    r.locale = _choose(ask, "Idioma / região (locale)", COMMON_LOCALES,
                       default="pt_PT.UTF-8")
    if backend.set_locale(r.locale):
        r.applied.append(f"locale={r.locale}")
    else:
        r.warnings.append(f"could not set locale {r.locale}")

    # --- 2. Timezone ---
    tz = _choose(ask, "Fuso horário", COMMON_TZ, default="Europe/Lisbon")
    valid = backend.list_timezones()
    if valid and tz not in valid:
        r.warnings.append(f"timezone {tz} not recognised; left unchanged")
    elif backend.set_timezone(tz):
        r.timezone = tz
        r.applied.append(f"timezone={tz}")
    else:
        r.warnings.append(f"could not set timezone {tz}")

    # --- 3. Keyboard layout ---
    km = _choose(ask, "Disposição do teclado", COMMON_KEYMAPS, default="pt-latin1")
    if backend.set_keymap(km):
        r.keymap = km
        r.applied.append(f"keymap={km}")
    else:
        r.warnings.append(f"could not set keymap {km}")

    # --- 4. Network: ethernet (auto) or Wi-Fi ---
    if backend.has_ethernet_carrier():
        choice = ask("Rede: Ethernet ligado por cabo foi detetado. Usar?",
                     options=["Ethernet", "Wi-Fi", "Saltar"], default="Ethernet")
    else:
        choice = ask("Rede", options=["Wi-Fi", "Saltar"], default="Wi-Fi")

    if choice == "Ethernet":
        r.network = "ethernet"
        r.applied.append("network=ethernet")
    elif choice == "Wi-Fi":
        nets = backend.wifi_scan()
        if not nets:
            r.network = "skipped"
            r.warnings.append("no Wi-Fi networks found")
        else:
            ssid = ask("Escolhe a rede Wi-Fi",
                       options=[n.ssid for n in nets[:12]], default=nets[0].ssid)
            secured = next((n.secured for n in nets if n.ssid == ssid), True)
            psk = ask(f"Palavra-passe de '{ssid}'", password=True) if secured else None
            if backend.wifi_connect(ssid, psk):
                r.network = f"wifi:{ssid}"
                r.applied.append(f"network=wifi:{ssid}")
            else:
                r.network = "skipped"
                r.warnings.append(f"could not connect to {ssid}")
    else:
        r.network = "skipped"

    return r
