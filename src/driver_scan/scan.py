from __future__ import annotations

from driver_scan.linux import scan_linux
from driver_scan.models import Report
from driver_scan.util import detect_family
from driver_scan.windows import scan_windows


def scan(
    family: str | None = None,
    *,
    include_windows_update: bool = True,
) -> Report:
    fam = (family or detect_family()).lower()
    if fam == "windows":
        return scan_windows(include_windows_update=include_windows_update)
    if fam == "linux":
        return scan_linux()
    report = scan_linux() if fam != "windows" else scan_windows()
    report.notes.append(f"Unknown OS family {fam!r}; attempted linux collect.")
    return report
