# Build & Recovery

## Order of operations (nothing destructive, nothing on firmware)

1. **Identify the console.** On the PS4 (once Linux boots a rescue shell) run
   `fusion-detect`, or match `lspci -nn` against `hardware/fusionhw/detect.py`.
   This fixes the kernel, the Mesa ceiling, and whether internal-HDD install is
   possible.
2. **Build Fusion Core** on a PC: `kernel/build-fusion-core.sh` (set
   `PS4_KERNEL_REPO`/`PS4_KERNEL_BRANCH` for your southbridge). It starts from
   the tree's `ps4_defconfig` so **all PS4 drivers/patches are preserved**, then
   merges `kernel/fusion-core.config` on top. It saves a `.config.bak` as a
   recovery config before building.
3. **Build the patched Mesa/RADV** from the community `[ps4]` repo, pinned per
   `mesa/README.md`. On Baikal/5.4, keep Mesa ≤ 25.1.
4. **Assemble the rootfs** (Arch/CachyOS Light base) and install the Fusion
   userspace with `installer/fusion-install.sh` (`ROOTFS_SRC=...`, `BZIMAGE=...`).
5. **Produce the loader trio** `bzImage + initramfs + psxitarch.tar.xz`, copy to
   a FAT32 USB, and boot via PS4-Linux-Loader + ps4-kexec on the jailbroken
   console.

## Recovery

- **Kernel won't boot:** keep the last known-good `bzImage` on the USB; the boot
  is non-destructive (Orbis is untouched), so power-cycling returns to the PS4
  menu. Swap back to the known-good kernel and initramfs.
- **GPU acceleration broke after an update:** you almost certainly pulled a Mesa
  past the ceiling. Reinstall the pinned Mesa (`mesa/fusion-mesa.pin.example`)
  and confirm with a `fusion-bench` run vs your saved baseline.
- **A performance profile made things worse:** `fusion-opt restore` returns every
  knob to its pre-profile value and restarts any stopped services.
- **A game prefix is wrecked:** prefixes are per-game under
  `$FUSION_HOME/prefixes/<id>`; delete that one; others are untouched.

## The promotion rule

A component moves from 📦 (config) to ✅ (working) **only** when:
1. it builds on a build host, and
2. it boots / runs on the target model, and
3. `benchmarks/fusion-bench compare` shows the result against a saved baseline.

Until all three hold, document it as untested. Do not invent compatibility.
