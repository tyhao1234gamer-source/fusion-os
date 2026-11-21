# PS4 Fusion OS

A lightweight, gaming-focused Linux distribution for the PlayStation 4, built as
a **tuned spin over the community PS4 Linux kernel + drivers** with an
**original userspace layer** (compatibility, optimization, interface,
benchmarking) built from scratch.

See `documentation/` and the Phase 1 technical report for the reasoning behind
the architecture. This README is the honest status of the repo.

## Design stance (why it is not "just Arch + Wine")

The hard, already-solved layers — the PS4 kernel fork, the kexec loader, the
patched Mesa/RADV drivers — are **inherited from the community, not reinvented**
(see the Phase 1 report). The engineering value, and all the from-scratch code
here, is in layers 4–7:

| Layer | Component | This repo | Status |
|---|---|---|---|
| 7 Measurement | **Fusion Benchmark** (`benchmarks/`) | original | ✅ runnable + tested |
| 6 Interface | **Fusion Gaming Shell** (`gaming-shell/`) | original | ✅ runnable + tested |
| 5 Optimization | **Fusion Performance Engine** (`optimizer/`) | original | ✅ runnable + tested |
| 4 Windows compat | **Fusion Compatibility Manager** (`compatibility-manager/`) | original | ✅ runnable + tested |
| 3 Graphics | Mesa/RADV pinning (`mesa/`, `graphics/`) | packaging | 📦 config, build-on-target |
| 2 Kernel | **Fusion Core** overlay (`kernel/`) | config | 📦 config, build-on-target |
| 1 Boot | loader trio + installer (`installer/`) | glue | 📦 skeleton, build-on-target |
| — | Hardware detection (`hardware/`) | original | ✅ runnable + tested |

✅ = real code that runs and passes unit tests here. 📦 = correct configuration /
scripts that must be **built and boot-tested on a real PS4** — they are not, and
cannot be, compiled or verified in a sandbox without the console. Per the
project rule, nothing in the 📦 rows is claimed "working" until a benchmark on
target says so.

## The four original tools (all stdlib-only, no pip needed on the console)

```
# Windows game compatibility: profiles, prefixes, DXVK/VKD3D, launch commands
compatibility-manager/fusion-compat  runtimes | add | list | doctor | run | report

# Reversible system tuning: EXTREME / COMPETITIVE / BALANCED / LOW
optimizer/fusion-opt                 list | plan | apply [--real] | status | restore

# Reproducible measurement vs baseline: idle RAM/CPU, FPS, 1% lows, frametimes
benchmarks/fusion-bench              idle | frames | baselines | compare

# Controller-first launcher, boots into tty1, no desktop environment
gaming-shell/fusion-shell            [--list | --render]

# Southbridge/GPU -> recommended kernel + Mesa pin
hardware/fusion-detect               [--pci vendor:device ...]
```

## Quick start (in this repo, no install)

```bash
./run-tests.sh                                  # run every component's tests
hardware/fusion-detect --pci 104d:908f 1002:9920
optimizer/fusion-opt plan extreme
compatibility-manager/fusion-compat --root /tmp/fh runtimes --roots <wine-dir>
```

## Requirements on target

- A jailbroken PS4 on a firmware with a public exploit (model/firmware decide
  everything — run `fusion-detect` first).
- Build host with network + x86-64 toolchain for the kernel/Mesa (not the PS4).
- The userspace tools need only Python 3 (stdlib) — they run on the console as-is.

## Safety rules baked into the project

- No firmware modification. No overclock / undervolt / fan-curve changes.
- Every optimization is snapshotted and reversible (`fusion-opt restore`).
- Claimed vs measured status are never conflated; only a real run sets measured.

## License

Original Fusion components: MIT (see `LICENSE`). Inherited kernel/Mesa/loader
components keep their upstream licenses — Fusion packages them, it does not
relicense them.
