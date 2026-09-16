from driver_scan.linux import parse_apt_upgradable, parse_firmware_log, parse_lspci, parse_lsusb

LSPCI = """
00:00.0 Host bridge [0600]: Intel Corporation Xeon E3-1200 v5 [8086:1904] (rev 08)
	Subsystem: Dell Device [1028:07a7]
00:02.0 VGA compatible controller [0300]: Intel Corporation Skylake-U GT2 [HD Graphics 520] [8086:1916] (rev 07)
	Subsystem: Dell Device [1028:07a7]
	Kernel driver in use: i915
	Kernel modules: i915
02:00.0 Network controller [0280]: Intel Corporation Wireless 8265 / 8275 [8086:24fd] (rev 78)
	Subsystem: Intel Corporation Device [8086:0050]
	Kernel modules: iwlwifi
03:00.0 Ethernet controller [0200]: Realtek Semiconductor Co., Ltd. RTL8111 [10ec:8168]
"""

LSUSB = """
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 001 Device 002: ID 1bcf:2b96 Sunplus Innovation Technology Inc. Integrated_Webcam_HD
Bus 001 Device 003: ID 8087:0a2b Intel Corp. Bluetooth wireless interface
Bus 001 Device 004: ID 0a5c:5834 Broadcom Corp. 5880
"""


def test_lspci_ok_missing_skip():
    findings = parse_lspci(LSPCI)
    by_slot = {f.id: f for f in findings}
    assert by_slot["pci:00:00.0"].severity == "skip"
    assert by_slot["pci:00:02.0"].severity == "ok"
    assert by_slot["pci:00:02.0"].driver == "i915"
    assert by_slot["pci:02:00.0"].severity == "missing"
    assert "iwlwifi" in by_slot["pci:02:00.0"].modules
    assert by_slot["pci:03:00.0"].severity == "missing"
    assert by_slot["pci:03:00.0"].vendor_id == "10ec"
    assert by_slot["pci:00:02.0"].official_url
    assert by_slot["pci:00:02.0"].category == "graphics"
    assert by_slot["pci:02:00.0"].category == "network"


def test_nouveau_is_mismatch():
    text = """
01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GP107 [10de:1cb3]
	Kernel driver in use: nouveau
	Kernel modules: nvidia, nouveau
"""
    findings = parse_lspci(text)
    assert findings[0].severity == "mismatch"
    assert findings[0].driver == "nouveau"


def test_lsusb_hub_vs_unbound():
    bound = {"1:1": "hub", "1:2": "uvcvideo", "1:3": "btusb", "1:4": None}
    findings = parse_lsusb(LSUSB, bound)
    kinds = {f.name: f.severity for f in findings}
    assert kinds["Linux Foundation 2.0 root hub"] == "skip"
    cam = [f for f in findings if "Webcam" in f.name][0]
    assert cam.category == "imaging"
    assert cam.severity == "ok"
    assert kinds["Intel Corp. Bluetooth wireless interface"] == "ok"
    assert kinds["Broadcom Corp. 5880"] == "missing"


def test_firmware_and_apt():
    fw = parse_firmware_log(
        "iwlwifi 0000:02:00.0: Direct firmware load for iwlwifi-7265D-29.ucode failed with error -2\n"
        "wmi_bus wmi_bus-PNP0C14:01: [Firmware Bug]: WQBC data block query control method not found\n",
        source="dmesg",
    )
    assert len(fw) == 1
    assert fw[0].severity == "firmware"
    assert "iwlwifi-7265D" in fw[0].detail
    apt = parse_apt_upgradable(
        "linux-firmware/kali-rolling 20260101 amd64 [upgradable from: 20250101]\n"
        "curl/kali-rolling 8.0 amd64 [upgradable from: 7.0]\n"
    )
    assert apt and apt[0].severity == "update"
    assert "linux-firmware" in apt[0].detail
    assert "curl" not in apt[0].detail
