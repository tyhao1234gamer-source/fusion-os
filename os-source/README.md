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
(~60-120 min) and uploads **`fusion-os.img`** — one disk image that boots on
**legacy BIOS and on UEFI (64- and 32-bit)**, from USB, SATA, NVMe or eMMC.

Write it to a USB and boot it:
```
sudo dd if=fusion-os.img of=/dev/sdX bs=4M status=progress oflag=sync
```

## Using the full edition

1. Write `fusion-os.img` to a USB stick (8 GB+; Rufus "DD mode" or
   balenaEtcher on Windows, `dd` on Linux) and boot it. BIOS (Legacy/CSM)
   and UEFI both work. **Secure Boot must be off** (see below).
2. GRUB menu: **Fusion OS** (max performance, CPU mitigations off),
   **safe** (mitigations on) or **recovery shell**.
3. First boot: the setup screen asks region, time zone, keyboard and
   Wi-Fi/Ethernet. No account, no sign-in.
4. Steam, Discord, Epic (Heroic), Firefox, MangoHud and gamescope download
   from Flathub once (needs the internet connection from step 3).
5. The **Fusion menu** opens: Steam first. Arrow keys / D-pad to move,
   Enter / A to open, Y to change the performance profile, B to quit.
   Closing an app brings the menu back. Log into Steam only if you want to.
6. **Bluetooth controllers** (DualSense, DualShock 4, Xbox, Switch Pro):
   menu entry *Bluetooth: ligar um comando* (full edition).
7. **Install on the PC's disk**: menu entry *Instalar o Fusion OS no disco*
   (or `sudo fusion-install-disk`). It lists the disks with their type
   (NVMe / SSD / HDD / USB / eMMC), refuses the USB you booted from and any
   mounted disk, and erases the chosen disk only after you type its name
   **and** `APAGAR`. The installed system boots on BIOS and UEFI, like the
   USB. Only the space in use is needed on the target, not the USB's size.

### Secure Boot

Fusion OS cannot boot with Secure Boot **on**: that needs a boot loader
signed by Microsoft, which only large distributions obtain. Turn it off in
the firmware setup (usually *Security* or *Boot* > *Secure Boot* >
*Disabled*). Windows on the same PC keeps working.

### What every CI build tests

The image is booted in QEMU on SATA disks and must report `FUSION_BOOT_OK`
with the Fusion tools running, on **UEFI 64-bit** and on **legacy BIOS**.
Also tested: 32-bit UEFI firmware (reported separately), and a full
**install test**: the installer runs inside the booted image onto a blank
disk, then that disk alone must boot (on BIOS) with its own root PARTUUID.
The kernel's final `.config` is checked against our fragments and published.
Logs: the `boot-test-<edition>` artifact. This is emulated hardware; real
machines still need real tests.

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
| `base` | boots on any x86-64 PC (BIOS or UEFI), Fusion tools, setup wizard, installer, wired network (Intel, Realtek incl. USB adapters, Broadcom, Atheros...) | `fusion_x86_64_defconfig` |
| `gaming` | + Mesa 24 (OpenGL: AMD radeonsi, Intel iris, nouveau), Vulkan (Intel ANV, lavapipe), GPU firmware, Wayland + `cage` fullscreen session, SDL2, PipeWire audio | base + `gaming.fragment` |
| `full` | + NetworkManager & Wi-Fi firmware (Intel, Realtek, MediaTek incl. Wi-Fi 7, Qualcomm ath9k/10k/11k/12k, Broadcom), Bluetooth (BlueZ + firmware), **Flatpak** (our own ostree/appstream/flatpak packages), Xwayland, unprivileged `fusion` session that boots into **Steam Big Picture**; Steam, Discord, Epic (Heroic) and Firefox come from Flathub, root partition grows to the whole disk | gaming + `full.fragment` |

Pick the edition in the workflow's **Run workflow** dialog.

Every build runs `validate-config.py`, which fails fast if Buildroot silently
dropped any requested option (an unmet dependency would otherwise only show up
as a broken system an hour later).

## Known hard limits of the from-source edition (honest)

- **Steam**: the client and most of Proton need 32-bit (i386) libraries next
  to the 64-bit ones; Buildroot builds one architecture and ships no Flatpak.
  The `full` edition solves this with **our own Buildroot packages** for
  OSTree 2026.7, AppStream 1.0.6 (+ a cross-compile patch) and Flatpak 1.16.6:
  Steam's Flatpak brings its own 32-bit runtime. Apps are fetched from Flathub
  on first boot (per user, no account), not baked into the image.
- **AMD Vulkan (RADV)** is not exposed by Buildroot's Mesa package; AMD GPUs
  get OpenGL now, Vulkan needs an extra package override.
- **NVIDIA**: Buildroot ships no NVIDIA firmware, so NVIDIA cards run nouveau
  without GSP firmware (limited performance).
- **Newest GPUs** (AMD RDNA4) need a newer kernel than 6.12; until then the
  menu falls back to software rendering instead of a black screen.
- **Intel laptop audio with SOF** (most Intel laptops since ~2020): no SOF
  firmware yet, so internal speakers/mic may not work; HDMI and USB audio do.
- **32-bit-only CPUs and ARM** are not supported (Steam/Proton are x86-64).

## Status (honest)

First-source milestone: compiles from source and boots to a login that runs the
Fusion tools and the first-run setup. The graphics/gaming stack (Mesa, then the
Steam/Proton frontier) is layered and **measured** from here — nothing is
claimed to run until a real boot proves it.
