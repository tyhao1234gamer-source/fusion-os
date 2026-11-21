# Fusion OS — built from source (Buildroot)

This is the **from-source** Fusion OS: the cross-toolchain, **glibc**, the
**Linux kernel** (with our config fragment), **systemd** and the base userland
are all **compiled from upstream source** by Buildroot. It is not a repackaged
distribution — nothing here is pulled as a pre-built distro package.

What is genuinely ours in this build:
- the Buildroot **external tree** (`br-external/`) defining the whole system,
- our **kernel config fragment** (`board/fusion/linux-fragment.config`),
- the **identity** (`/etc/os-release`, hostname, boot-to-session),
- the **Fusion tools** (compat manager, optimizer, benchmark, gaming shell,
  hardware auto-detect, setup wizard) installed into the image.

What is still inherited (by necessity — nobody writes these from scratch):
- the Linux kernel source, glibc, systemd, coreutils (all compiled here from
  source, but authored upstream),
- later, the gaming stack (Mesa/Vulkan compiles from source in Buildroot;
  Steam/Proton are Valve's closed binaries and are the hard frontier).

## Build it (on GitHub, from source)

Push and run the **"Build Fusion OS from source (Buildroot)"** workflow
(`.github/workflows/build-os.yml`). GitHub compiles everything from source
(~60-120 min) and uploads **`fusion-os.img`** — a USB-bootable UEFI disk image.

Write it to a USB and boot (UEFI):
```
sudo dd if=fusion-os.img of=/dev/sdX bs=4M status=progress oflag=sync
```

## Build it locally (needs a Linux host + internet, no Arch required)

```bash
scripts/install-fusion-userspace.sh os-source/br-external/board/fusion/rootfs-overlay
git clone --depth 1 --branch 2025.02.x https://github.com/buildroot/buildroot.git
make -C buildroot BR2_EXTERNAL="$PWD/os-source/br-external" O="$PWD/output" fusion_x86_64_defconfig
make -C buildroot O="$PWD/output"
# -> output/images/fusion-os.img
```

## Editions

| Edition | What it adds | Defconfig |
|---|---|---|
| `base` | boots from USB on any UEFI PC, Fusion tools, setup wizard | `fusion_x86_64_defconfig` |
| `gaming` | + Mesa 24 (OpenGL: AMD radeonsi, Intel iris, nouveau), Vulkan (Intel ANV, lavapipe), GPU firmware, Wayland + `cage` fullscreen session, SDL2, PipeWire audio | base + `gaming.fragment` (combined at build time) |

Pick the edition in the workflow's **Run workflow** dialog.

Every build runs `validate-config.py`, which fails fast if Buildroot silently
dropped any requested option (an unmet dependency would otherwise only show up
as a broken system an hour later).

## Known hard limits of the from-source edition (honest)

- **Steam**: the Steam client and most of Proton need 32-bit (i386) libraries
  installed next to the 64-bit ones ("multilib"). Buildroot builds a single
  architecture, and it does not package Flatpak (Steam's Flatpak brings its
  own 32-bit runtime). So Steam does **not** run on this edition yet. Paths
  forward: package Flatpak + OSTree ourselves, or build a second i386 sysroot.
- **AMD Vulkan (RADV)** is not exposed by Buildroot's Mesa package; AMD GPUs
  get OpenGL now, Vulkan needs an extra package override.
- **NVIDIA**: Buildroot ships no NVIDIA firmware, so NVIDIA cards run nouveau
  without GSP firmware (limited performance).

## Status (honest)

First-source milestone: compiles from source and boots to a login that runs the
Fusion tools and the first-run setup. The graphics/gaming stack (Mesa, then the
Steam/Proton frontier) is layered and **measured** from here — nothing is
claimed to run until a real boot proves it.
