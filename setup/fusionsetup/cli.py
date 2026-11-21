"""TTY front-end for the setup wizard.

A simple numbered-menu prompter that works on any console (no curses needed,
which is the right call for a first-boot screen). Runs once; writes a stamp so
it never runs again. No account step.
"""

from __future__ import annotations

import json
import os
import sys

from .backend import SystemBackend
from .wizard import run_wizard

STAMP = "/etc/fusion/.setup-done"


def _menu_ask(prompt, options=None, default=None, password=False) -> str:
    if password:
        import getpass
        return getpass.getpass(f"{prompt}: ")
    print(f"\n{prompt}")
    if options:
        for i, opt in enumerate(options, 1):
            mark = " (padrão)" if opt == default else ""
            print(f"  {i}) {opt}{mark}")
        print("  0) outro (escrever manualmente)")
        while True:
            raw = input(f"Escolhe [1-{len(options)}, 0, Enter=padrão]: ").strip()
            if raw == "" and default is not None:
                return default
            if raw == "0":
                return input("Valor: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(options):
                return options[int(raw) - 1]
            print("  opção inválida")
    else:
        raw = input(f"{prompt}" + (f" [{default}]" if default else "") + ": ").strip()
        return raw or (default or "")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    force = "--force" in argv
    if os.path.exists(STAMP) and not force:
        return 0  # already configured; stay quiet

    print("=" * 50)
    print("  FUSION OS — configuração inicial")
    print("  (sem conta, sem login na nuvem)")
    print("=" * 50)

    result = run_wizard(SystemBackend(), _menu_ask)

    print("\nConfiguração aplicada:")
    for a in result.applied:
        print(f"  ✓ {a}")
    for w in result.warnings:
        print(f"  ! {w}")

    os.makedirs("/etc/fusion", exist_ok=True)
    try:
        with open("/etc/fusion/setup.json", "w", encoding="utf-8") as fh:
            json.dump(result.as_dict(), fh, indent=2)
        open(STAMP, "w").close()
    except OSError as e:
        print(f"  ! could not persist setup: {e}")
    print("\nPronto. A iniciar o Fusion...\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
