from __future__ import annotations

from pathlib import Path

from driver_scan.models import Report
from driver_scan.vendors import oem_from_text


def read_dmi() -> tuple[str, str, str]:
    root = Path("/sys/class/dmi/id")
    vendor = _dmi(root / "sys_vendor")
    product = _dmi(root / "product_name")
    serial = _dmi(root / "product_serial")
    return vendor, product, serial


def apply_chassis(
    report: Report,
    vendor: str | None,
    model: str | None,
    serial: str | None,
) -> None:
    blob = " ".join(p for p in (vendor, model) if p)
    label, url = oem_from_text(blob)
    report.oem = label or (vendor or None)
    report.model = model or None
    if serial and serial.lower() not in {"", "none", "to be filled by o.e.m.", "system serial number"}:
        report.serial = serial
    report.oem_url = url
    if report.oem_url:
        for f in report.findings:
            if f.severity in {"missing", "error", "firmware"} and report.oem_url not in f.suggested:
                f.suggested.append(f"PC maker support: {report.oem_url}")


def _dmi(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
