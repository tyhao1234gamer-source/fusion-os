"""Tests for universal machine detection against fake /proc and /sys trees."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fusionhw import machine as M  # noqa: E402


def fake_tree(cpu_vendor="AuthenticAMD", cpu_flags="fpu avx avx2 sse4_2",
              cores=8, mem_kb=8000000, gpus=None, disks=None):
    """Build a fake /proc and /sys and return (proc_root, sys_root)."""
    root = tempfile.mkdtemp()
    proc = os.path.join(root, "proc")
    sysr = os.path.join(root, "sys")
    os.makedirs(proc)
    # cpuinfo
    blocks = []
    for i in range(cores):
        blocks.append(f"processor\t: {i}\nvendor_id\t: {cpu_vendor}\n"
                      f"model name\t: Fake CPU @ 2.0GHz\nflags\t\t: {cpu_flags}\n")
    open(os.path.join(proc, "cpuinfo"), "w").write("\n".join(blocks))
    open(os.path.join(proc, "meminfo"), "w").write(f"MemTotal:       {mem_kb} kB\n")
    # PCI GPUs
    pci = os.path.join(sysr, "bus/pci/devices")
    os.makedirs(pci)
    for idx, (vendor, device, cls) in enumerate(gpus or []):
        d = os.path.join(pci, f"0000:0{idx}:00.0")
        os.makedirs(d)
        open(os.path.join(d, "class"), "w").write(cls + "\n")
        open(os.path.join(d, "vendor"), "w").write(vendor + "\n")
        open(os.path.join(d, "device"), "w").write(device + "\n")
    # block devices
    blk = os.path.join(sysr, "block")
    os.makedirs(blk)
    for name, rotational in (disks or []):
        q = os.path.join(blk, name, "queue")
        os.makedirs(q)
        open(os.path.join(q, "rotational"), "w").write(f"{rotational}\n")
    return proc, sysr


class TestMachine(unittest.TestCase):
    def test_amd_laptop_nvme_ssd(self):
        proc, sysr = fake_tree(
            gpus=[("0x1002", "0x15d8", "0x030000")],       # AMD iGPU
            disks=[("nvme0n1", 0)])
        m = M.detect(proc, sysr)
        self.assertEqual(m.cpu.vendor, "amd")
        self.assertTrue(m.cpu.has_avx2)
        self.assertEqual(m.gpus[0].vendor, "amd")
        self.assertEqual(m.mem_total_mb, 8000000 // 1024)
        tune = M.plan_tuning(m)
        self.assertEqual(tune.io_scheduler["nvme0n1"], "none")
        self.assertEqual(tune.cpu_pin_hint, "half")

    def test_nvidia_triggers_proprietary_plan(self):
        proc, sysr = fake_tree(gpus=[("0x10de", "0x1f99", "0x030000")],
                               disks=[("sda", 1)])  # HDD
        m = M.detect(proc, sysr)
        plan = M.plan_drivers(m)
        self.assertTrue(plan.nvidia_proprietary)
        self.assertEqual(M.plan_tuning(m).io_scheduler["sda"], "bfq")  # HDD->bfq

    def test_intel_igpu_and_avx2_absent_warns(self):
        proc, sysr = fake_tree(cpu_vendor="GenuineIntel",
                               cpu_flags="fpu sse4_2",  # no avx2
                               gpus=[("0x8086", "0x9a49", "0x030000")],
                               disks=[("sda", 0)])
        m = M.detect(proc, sysr)
        self.assertFalse(m.cpu.has_avx2)
        self.assertIn("vulkan-intel (ANV)", M.plan_drivers(m).vulkan_icds)
        self.assertTrue(any("AVX2" in n for n in M.plan_tuning(m).notes))

    def test_dual_gpu_hybrid(self):
        proc, sysr = fake_tree(gpus=[("0x8086", "0x9a49", "0x030000"),
                                     ("0x10de", "0x1f99", "0x030200")],
                               disks=[("nvme0n1", 0)])
        m = M.detect(proc, sysr)
        vendors = {g.vendor for g in m.gpus}
        self.assertEqual(vendors, {"intel", "nvidia"})
        plan = M.plan_drivers(m)
        self.assertTrue(plan.nvidia_proprietary)

    def test_low_ram_small_zram(self):
        proc, sysr = fake_tree(mem_kb=2000000, cores=2)  # 2 GB, dual-core
        m = M.detect(proc, sysr)
        tune = M.plan_tuning(m)
        self.assertEqual(tune.zram_mb, (2000000 // 1024) // 2)
        self.assertEqual(tune.cpu_pin_hint, "")  # too few cores to pin


if __name__ == "__main__":
    unittest.main()
