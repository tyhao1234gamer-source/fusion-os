# Fusion OS — bootable ISO (weak x86-64 laptop)

A lightweight Arch-based gaming spin that boots straight into a gaming session
(gamescope + Steam Big Picture, or the Fusion Gaming Shell) with the Fusion
performance tools built in. Built **on top of the official Arch `releng`
profile** — Fusion is the overlay, not a fork.

## Honest note on building

The `.iso` is **not** and **cannot be** built inside the Fusion dev sandbox: it
needs internet (to download packages), root, and `mkarchiso`. `build-iso.sh` is
the recipe you run on an Arch host to produce it. The parts that are pure logic
(the userspace install, the overlay, the tuning) are tested; the final image
must be built and boot-tested by you.

## Build it

On an Arch Linux host (or `archlinux` container) with internet:

```bash
sudo pacman -S archiso
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
