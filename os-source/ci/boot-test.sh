#!/usr/bin/env bash
# Boot a Fusion OS disk image in QEMU and wait for a marker on the serial port.
#
#   boot-test.sh <firmware> <image> <marker> <log> [extra-disk]
#
#   firmware: uefi    64-bit UEFI (OVMF)
#             uefi32  32-bit UEFI (OVMF ia32) with a 64-bit CPU
#             bios    legacy BIOS (SeaBIOS, QEMU's default)
#
# Disks are SATA (AHCI), as on a real PC: the image is the first disk, the
# optional extra disk the second. Exit 0 only if <marker> appears.
set -u
fw=$1 img=$2 marker=$3 log=$4 extra=${5:-}

accel=()
if [ -e /dev/kvm ]; then sudo chmod 666 /dev/kvm; accel=(-enable-kvm -cpu host); fi

machine=q35
firmware=()
case "$fw" in
    uefi)
        code=$(ls /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd 2>/dev/null | head -1)
        vars=$(ls /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd 2>/dev/null | head -1)
        ;;
    uefi32)
        code=$(ls /usr/share/OVMF/OVMF32_CODE_4M.fd /usr/share/OVMF/OVMF32_CODE_4M.secboot.fd 2>/dev/null | head -1)
        vars=$(ls /usr/share/OVMF/OVMF32_VARS_4M.fd 2>/dev/null | head -1)
        case "$code" in *secboot*)
            machine=q35,smm=on
            firmware+=(-global driver=cfi.pflash01,property=secure,value=on) ;;
        esac
        ;;
    bios) code="" ;;
    *) echo "unknown firmware $fw"; exit 2 ;;
esac
if [ "$fw" != bios ]; then
    [ -n "$code" ] && [ -n "$vars" ] || { echo "no OVMF firmware for $fw"; exit 3; }
    cp "$vars" "vars-$fw.fd"
    firmware+=(-drive "if=pflash,format=raw,readonly=on,file=$code"
               -drive "if=pflash,format=raw,file=vars-$fw.fd")
fi

# q35 has an ICH9 AHCI controller built in: ide.0 / ide.1 are SATA ports.
disks=(-drive "file=$img,format=raw,if=none,id=d0" -device ide-hd,drive=d0,bus=ide.0,bootindex=1)
[ -n "$extra" ] && disks+=(-drive "file=$extra,format=raw,if=none,id=d1" -device ide-hd,drive=d1,bus=ide.1)

: > "$log"
echo "boot-test: firmware=$fw image=$img extra=${extra:-none} marker=$marker"
qemu-system-x86_64 "${accel[@]}" -machine "$machine" -m 4096 -smp 2 \
    "${firmware[@]}" "${disks[@]}" \
    -nic user,model=e1000 -display none -serial "file:$log" &
qpid=$!
ok=0
for _ in $(seq 1 240); do          # up to ~20 minutes (the install test copies the system)
    grep -q "$marker" "$log" && { ok=1; break; }
    grep -q "FUSION_INSTALL_FAILED" "$log" && break
    kill -0 $qpid 2>/dev/null || break
    sleep 5
done
kill $qpid 2>/dev/null || true
wait $qpid 2>/dev/null || true
echo "================ serial console ($fw) ================"
tr -d '\r' < "$log" | tail -n 120
echo "======================================================"
if [ $ok = 1 ]; then echo "BOOT TEST PASSED ($fw: $marker)"; exit 0; fi
echo "BOOT TEST FAILED ($fw: $marker)"
exit 1
