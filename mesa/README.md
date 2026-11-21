# Fusion Graphics — Mesa / RADV for the PS4 (Liverpool / Neo)

The PS4 GPU 3D acceleration that was broken in 2015 (GPUVM / command-buffer page
faults) is **working today** through community-patched Mesa, libdrm and
`xf86-video-amdgpu`. Fusion OS does **not** rewrite any of this — it packages the
community drivers and pins versions correctly per southbridge.

## The hard rule: pin Mesa by southbridge

| Southbridge / kernel | Mesa version | Why |
|---|---|---|
| Aeolia / Belize (6.15.x) | latest (25.3+) | Works with current Mesa |
| Baikal, or any 5.4.x kernel | **≤ 25.1** | Newer Mesa **breaks** GPU acceleration |

`hardware/fusion-detect` returns the correct pin; the installer writes it into
pacman config so `pacman -Syu` can never pull a Mesa that breaks the GPU.

## Where the patched drivers come from (do not reinvent)

- `ps4-radeon-patches` (fail0verflow) — libdrm/mesa/xf86-video-ati PCI-ID + chip-type patches
- `ps4linux-video-drivers` (Ps3itaTeam) — Arch packages + `[ps4]` pacman repo
- `ps4-video-archlinux` (DionKill) — up-to-date patched mesa/libdrm/xf86-video-amdgpu

## Pinning example (installed by the installer)

`/etc/pacman.conf` IgnorePkg + the `[ps4]` repo, so the patched, version-pinned
packages win over stock Arch Mesa. See `fusion-mesa.pin.example` in this folder.

> Build + boot test on the target model before declaring any Mesa version good.
> A benchmark vs baseline (see `benchmarks/`) is what promotes "works" from a
> claim to a fact.
