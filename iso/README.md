# Fusion OS — bootable ISO (weak x86-64 laptop)

A lightweight Arch-based gaming spin that boots straight into a gaming session
(gamescope + Steam Big Picture, or the Fusion Gaming Shell) with the Fusion
performance tools built in. Built **on top of the official Arch `releng`
profile** — Fusion is the overlay, not a fork.

## How to get the real .iso (pick one)

The `.iso` must download hundreds of packages, so it is built where there is
open internet. The whole build pipeline (overlay, user, tuning, package list)
is tested end-to-end with a stubbed `mkarchiso`; these are the ways to run the
real thing.

### Option 1 — Let GitHub build it (no Arch, no Docker, recommended)

Push this repo to GitHub, then:

- **Actions tab → "Build Fusion OS ISO" → Run workflow**, or
- `git tag v0.4 && git push --tags`

GitHub builds the ISO on its own runners (full internet, Arch container) and
uploads it. Download it from the run's **Artifacts** (`fusion-os-iso`), or — for
a tag — from the auto-created **Release**. A `SHA256SUMS.txt` is included.
Workflow: `.github/workflows/build-iso.yml`.

### Option 2 — Build with Docker on any machine (Windows/Mac/Linux)

```bash
./iso/build-in-docker.sh         # runs the build inside an Arch container
# -> ./out/fusion-os-*.iso
```

Needs Docker + internet. No Arch install required.

### Option 3 — Native Arch host

```bash
sudo pacman -S archiso python
sudo ./iso/build-iso.sh          # -> ./out/fusion-os-*.iso
```

What the script does: copies the releng profile, appends `overlay/packages.x86_64`,
lays the overlay airootfs (autologin, session, zram, sysctl, graphics env),
creates the `fusion` autologin user, installs the five Fusion tools into
`/usr/lib/fusion` + `/usr/bin`, enables NetworkManager, and runs `mkarchiso`.

## Write it to USB and boot

```bash
sudo dd if=out/fusion-os-*.iso of=/dev/sdX bs=4M status=progress oflag=sync
```

Boot the laptop from the USB → it auto-logs in as `fusion` and runs
`fusion-session` → gamescope hosts Steam Big Picture (or the Fusion Gaming Shell
if Steam/gamescope aren't present).

## Install to the laptop's disk

The live ISO is a trial. To install permanently:

1. From the live session (switch to a shell on tty2 with Ctrl+Alt+F2), run
   `archinstall` → choose the **minimal** profile, enable **multilib**.
2. Reboot into the new install, copy this repo over, and run:
   ```bash
   sudo ./scripts/fusion-postinstall.sh
   ```
   That installs the gaming stack + Fusion tools + autologin onto the real disk.

## GPU driver notes (matters on a weak laptop)

- **AMD** and **Intel**: fully covered by the open Mesa/RADV/ANV packages in the
  list — nothing extra to do. The performance profiles drive `amdgpu`'s
  `power_dpm_force_performance_level` directly.
- **NVIDIA**: the list ships the open `nouveau`/`vulkan-nouveau` stack, which is
  weak for gaming. For an NVIDIA laptop, add the proprietary driver
  (`nvidia`/`nvidia-dkms` + `lib32-nvidia-utils`) to `packages.x86_64` before
  building, or install it via `fusion-postinstall` on disk. Tell me the GPU and
  I'll wire the exact packages + `nvidia-drm.modeset` boot params.

## AUR packages

A few entries (`dxvk-bin`, `xpadneo-dkms`) are AUR-only. `mkarchiso` builds from
official repos; install those from the AUR after first boot, or drop them — DXVK
is also installed per-prefix by the Compatibility Manager, and DualShock 4 pads
work via the in-kernel `hid-sony` without `xpadneo`.
