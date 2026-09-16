from __future__ import annotations

Category = str

GENERIC_DISPLAY = (
    "microsoft basic display",
    "standard vga",
    "basic display adapter",
    "standard vga graphics adapter",
)
LINUX_GRAPHICS_FALLBACK = frozenset({"nouveau", "vesa", "simpledrm", "simple-framebuffer", "bochs-drm"})

# Windows codes that usually mean the installed package does not match this OS/device.
CM_MISMATCH = frozenset({32, 39, 48})


def category_from_pci(class_code: str) -> Category:
    cc = (class_code or "").lower()
    if cc.startswith("03"):
        return "graphics"
    if cc.startswith("04"):
        return "audio"
    if cc in {"0200", "0280"}:
        return "network"
    if cc.startswith("01"):
        return "storage"
    if cc.startswith("06") or cc.startswith("05") or cc.startswith("11"):
        return "chipset"
    if cc.startswith("0c"):
        return "usb"
    return "other"


def category_from_pnp(class_name: str, name: str = "") -> Category:
    c = (class_name or "").lower()
    n = (name or "").lower()
    if c in {"display", "monitor"} or "vga" in n or "graphics" in n or "gpu" in n:
        return "graphics"
    if c in {"media", "audioendpoint", "sound"} or "audio" in n:
        return "audio"
    if c in {"net", "bluetooth"} or "ethernet" in n or "wi-fi" in n or "wifi" in n:
        return "network"
    if c in {"scsiadapter", "hdc", "nvme"} or "nvme" in n or "sata" in n or "ahci" in n:
        return "storage"
    if c in {"printer", "printqueue"} or "printer" in n:
        return "printer"
    if c in {"image", "camera"} or "webcam" in n or "scanner" in n or "camera" in n:
        return "imaging"
    if c in {"usb", "usbdevice"}:
        return "usb"
    if c in {"system", "computer", "processor"}:
        return "chipset"
    return "other"


def category_from_usb_name(name: str) -> Category:
    n = (name or "").lower()
    if "printer" in n:
        return "printer"
    if "webcam" in n or "camera" in n or "scanner" in n:
        return "imaging"
    if "hub" in n or "root hub" in n:
        return "usb"
    return "usb"


def linux_mismatch(vendor_id: str | None, driver: str | None, category: str) -> str | None:
    drv = (driver or "").lower()
    ven = (vendor_id or "").lower()
    if category == "graphics" and drv in LINUX_GRAPHICS_FALLBACK:
        if ven == "10de" and drv == "nouveau":
            return "NVIDIA GPU bound to nouveau fallback, not the vendor module."
        if drv in {"vesa", "simpledrm", "simple-framebuffer", "bochs-drm"}:
            return f"Graphics using fallback driver {drv}."
        if ven == "10de":
            return "NVIDIA GPU bound to a fallback driver."
    return None


def windows_mismatch(
    *,
    name: str,
    class_name: str,
    code: int,
    category: str,
) -> str | None:
    if code in CM_MISMATCH:
        return f"Device Manager code {code}: package does not match this device or Windows version."
    n = (name or "").lower()
    if category == "graphics" and any(g in n for g in GENERIC_DISPLAY):
        return "Display is using a generic Windows adapter, not the GPU vendor driver."
    return None
