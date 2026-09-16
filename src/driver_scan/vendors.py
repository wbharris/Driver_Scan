"""Official vendor / OEM support pages. No third-party driver-pack sites."""

from __future__ import annotations

# PCI / USB vendor ID (lowercase) -> (short name, support URL)
VENDOR_SUPPORT: dict[str, tuple[str, str]] = {
    "8086": ("Intel", "https://www.intel.com/content/www/us/en/download-center/home.html"),
    "8087": ("Intel", "https://www.intel.com/content/www/us/en/download-center/home.html"),
    "10de": ("NVIDIA", "https://www.nvidia.com/Download/index.aspx"),
    "1002": ("AMD", "https://www.amd.com/en/support"),
    "1022": ("AMD", "https://www.amd.com/en/support"),
    "10ec": ("Realtek", "https://www.realtek.com/en/downloads"),
    "14e4": ("Broadcom", "https://www.broadcom.com/support/download-search"),
    "0a5c": ("Broadcom", "https://www.broadcom.com/support/download-search"),
    "1969": ("Qualcomm Atheros", "https://www.qualcomm.com/support"),
    "168c": ("Qualcomm Atheros", "https://www.qualcomm.com/support"),
    "17aa": ("Lenovo", "https://support.lenovo.com/"),
    "1028": ("Dell", "https://www.dell.com/support/home"),
    "103c": ("HP", "https://support.hp.com/drivers"),
    "1462": ("MSI", "https://www.msi.com/support"),
    "1043": ("ASUS", "https://www.asus.com/support/download-center/"),
    "1849": ("ASRock", "https://www.asrock.com/support/"),
    "15d9": ("Supermicro", "https://www.supermicro.com/support"),
    "1d6b": ("Linux Foundation", "https://www.kernel.org/"),
    "046d": ("Logitech", "https://support.logi.com/"),
    "045e": ("Microsoft", "https://www.microsoft.com/download"),
    "1bcf": ("Sunplus / OEM webcam", "https://www.dell.com/support/home"),
    "05e3": ("Genesys Logic", "https://www.genesyslogic.com/"),
    "17e9": ("DisplayLink", "https://www.synaptics.com/products/displaylink-graphics/downloads"),
    "06c4": ("Bizlink / Dell dock", "https://www.dell.com/support/home"),
    "0bda": ("Realtek", "https://www.realtek.com/en/downloads"),
}

OEM_BY_NAME: list[tuple[str, str, str]] = [
    ("dell", "Dell", "https://www.dell.com/support/home"),
    ("lenovo", "Lenovo", "https://support.lenovo.com/"),
    ("thinkpad", "Lenovo", "https://support.lenovo.com/"),
    ("hewlett", "HP", "https://support.hp.com/drivers"),
    (" hp ", "HP", "https://support.hp.com/drivers"),
    ("asus", "ASUS", "https://www.asus.com/support/download-center/"),
    ("acer", "Acer", "https://www.acer.com/support"),
    ("microsoft", "Microsoft", "https://support.microsoft.com/windows"),
    ("surface", "Microsoft", "https://support.microsoft.com/surface"),
]


def official_url(vendor_id: str | None, name: str = "") -> str | None:
    if vendor_id:
        hit = VENDOR_SUPPORT.get(vendor_id.lower())
        if hit:
            return hit[1]
    lowered = f" {name.lower()} "
    for needle, _label, url in OEM_BY_NAME:
        if needle in lowered:
            return url
    return None


def vendor_label(vendor_id: str | None) -> str | None:
    if not vendor_id:
        return None
    hit = VENDOR_SUPPORT.get(vendor_id.lower())
    return hit[0] if hit else None


def oem_from_text(text: str) -> tuple[str | None, str | None]:
    """Return (label, support_url) from chassis vendor/model text."""
    lowered = f" {text.lower()} "
    for needle, label, url in OEM_BY_NAME:
        if needle in lowered:
            return label, url
    return None, None
