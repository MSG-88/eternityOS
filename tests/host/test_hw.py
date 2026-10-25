"""Hardware inventory: parsing, judgement and the report on a synthetic sysfs, plus a run on
the real host (whatever it is) that must never raise. Run: python3 -m unittest tests/host/test_hw.py"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "config", "includes.chroot", "usr", "lib", "eternity", "py"))

from eternity import hw  # noqa: E402

LSPCI = """00:00.0 Host bridge: Advanced Micro Devices, Inc. [AMD] Raven/Raven2 Root Complex
\tSubsystem: Micro-Star International Co., Ltd. [MSI] Raven/Raven2 Root Complex
01:00.0 VGA compatible controller: Advanced Micro Devices, Inc. [AMD/ATI] Navi 14 [Radeon RX 5500M]
\tSubsystem: Micro-Star International Co., Ltd. [MSI] Navi 14 [Radeon RX 5500M]
\tKernel driver in use: amdgpu
\tKernel modules: amdgpu
02:00.0 Network controller: Realtek Semiconductor Co., Ltd. RTL8822CE 802.11ac PCIe Wireless Network Adapter
\tSubsystem: AzureWave Device 3751
\tKernel modules: rtw88_8822ce
03:00.0 Ethernet controller: Realtek Semiconductor Co., Ltd. Killer E2600 GbE Controller (rev 21)
\tKernel driver in use: r8169
\tKernel modules: r8169
"""


def fake_sysfs(root: str, wifi_driver: bool) -> None:
    def put(rel, content):
        p = os.path.join(root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(content)
    devs = {"0000:01:00.0": ("0x030000", "0x1002", "0x7340", "amdgpu"),
            "0000:02:00.0": ("0x028000", "0x10ec", "0xc822", "rtw88_8822ce" if wifi_driver else None),
            "0000:03:00.0": ("0x020000", "0x10ec", "0x2600", "r8169")}
    for slot, (cls, ven, dev, drv) in devs.items():
        base = f"sys/bus/pci/devices/{slot}"
        put(f"{base}/class", cls + "\n"); put(f"{base}/vendor", ven + "\n"); put(f"{base}/device", dev + "\n")
        if drv:
            os.makedirs(os.path.join(root, "sys/bus/pci/drivers", drv), exist_ok=True)
            os.symlink(os.path.join(root, "sys/bus/pci/drivers", drv), os.path.join(root, base, "driver"))
    put("sys/bus/usb/devices/1-4/idVendor", "13d3\n"); put("sys/bus/usb/devices/1-4/idProduct", "3549\n")
    put("sys/bus/usb/devices/1-4/product", "Bluetooth Radio\n"); put("sys/bus/usb/devices/1-4/bDeviceClass", "e0\n")
    os.makedirs(os.path.join(root, "sys/bus/usb/drivers/btusb"), exist_ok=True)
    os.makedirs(os.path.join(root, "sys/bus/usb/devices/1-4/1-4:1.0"), exist_ok=True)
    os.symlink(os.path.join(root, "sys/bus/usb/drivers/btusb"), os.path.join(root, "sys/bus/usb/devices/1-4/1-4:1.0/driver"))
    put("sys/class/dmi/id/sys_vendor", "Micro-Star International Co., Ltd.\n")
    put("sys/class/dmi/id/product_name", "Alpha 15 A3DDK\n")
    put("sys/class/dmi/id/bios_version", "E16U6AMS.111\n"); put("sys/class/dmi/id/bios_date", "05/28/2020\n")
    put("sys/class/power_supply/BAT1/type", "Battery\n"); put("sys/class/power_supply/BAT1/capacity", "77\n")
    put("sys/class/power_supply/BAT1/status", "Discharging\n")
    put("sys/class/backlight/amdgpu_bl1/brightness", "120\n"); put("sys/class/backlight/amdgpu_bl1/max_brightness", "255\n")
    put("sys/power/state", "freeze mem disk\n")
    put("sys/class/drm/card1/device/vendor", "0x1002\n"); put("sys/class/drm/card1/device/device", "0x15d8\n")
    os.symlink(os.path.join(root, "sys/bus/pci/drivers/amdgpu"), os.path.join(root, "sys/class/drm/card1/device/driver"))
    put("sys/class/drm/card1-eDP-1/status", "connected\n")
    put("proc/cpuinfo", "model name\t: AMD Ryzen 7 3750H with Radeon Vega Mobile Gfx\nmicrocode\t: 0x8108109\n")
    put("proc/meminfo", "MemTotal:       14680064 kB\nMemAvailable:    9000000 kB\n")
    put("proc/asound/cards", " 0 [Generic        ]: HDA-Intel - HD-Audio Generic\n                      HD-Audio Generic at 0xfc500000 irq 90\n")
    put("proc/bus/input/devices", 'I: Bus=0018 Vendor=06cb Product=ce2d Version=0100\nN: Name="SYNA7DB5:00 06CB:CE2D Touchpad"\nH: Handlers=mouse0 event7\n\n')
    put("proc/sys/kernel/osrelease", "6.12.48+deb13-amd64\n")


class TestParse(unittest.TestCase):
    def test_lspci_blocks(self):
        devs = hw.parse_lspci_k(LSPCI)
        self.assertEqual(len(devs), 4)
        wifi = next(d for d in devs if "RTL8822CE" in d["description"])
        self.assertEqual(wifi["driver"], "")
        self.assertEqual(wifi["modules"], "rtw88_8822ce")
        eth = next(d for d in devs if "E2600" in d["description"])
        self.assertEqual(eth["driver"], "r8169")


class TestSynthetic(unittest.TestCase):
    def inventory(self, wifi_driver: bool):
        tmp = tempfile.mkdtemp()
        fake_sysfs(tmp, wifi_driver)
        old = hw.SYS, hw.PROC
        hw.SYS, hw.PROC = os.path.join(tmp, "sys"), os.path.join(tmp, "proc")
        try:
            return hw.inventory()
        finally:
            hw.SYS, hw.PROC = old

    def test_healthy_laptop(self):
        inv = self.inventory(wifi_driver=True)
        self.assertEqual(inv["platform"]["product"], "Alpha 15 A3DDK")
        self.assertEqual(inv["platform"]["memory_gb"], 14.0)
        pci = {d["slot"]: d for d in inv["pci"]}
        self.assertEqual(pci["02:00.0"]["driver"], "rtw88_8822ce")
        self.assertEqual(pci["02:00.0"]["kind"], "network")
        self.assertEqual(inv["usb"][0]["drivers"], ["btusb"])
        self.assertEqual(inv["graphics"]["cards"][0]["driver"], "amdgpu")
        self.assertEqual(inv["graphics"]["connected_outputs"], ["card1-eDP-1"])
        self.assertTrue(inv["power"]["suspend_supported"])
        bad = [m for s, m in hw.problems(inv) if s == "bad"]
        self.assertEqual([m for m in bad if "without a driver" in m], [])
        text = hw.report(inv)
        self.assertIn("Alpha 15", text)
        self.assertIn("✓ Realtek Semiconductor", text) if "Realtek" in text else self.assertIn("[rtw88_8822ce]", text)
        json.dumps(inv)  # serialisable

    def test_wifi_without_driver_is_a_problem(self):
        inv = self.inventory(wifi_driver=False)
        probs = hw.problems(inv)
        self.assertTrue(any(s == "bad" and "network device without a driver" in m for s, m in probs), probs)
        self.assertFalse(hw.summary(inv)["ok"])
        self.assertIn("✗", hw.report(inv))


class TestRealHost(unittest.TestCase):
    def test_runs_anywhere(self):
        inv = hw.inventory()
        self.assertIn("platform", inv)
        hw.report(inv)
        hw.problems(inv)
        json.dumps(inv)


if __name__ == "__main__":
    unittest.main()
