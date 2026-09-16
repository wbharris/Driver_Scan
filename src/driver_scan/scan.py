from __future__ import annotations

import json
from pathlib import Path

from driver_scan.filters import apply_view_filters
from driver_scan.ignore import apply_ignore, load_ignored
from driver_scan.linux import scan_linux
from driver_scan.models import Report
from driver_scan.util import detect_family
from driver_scan.windows import report_from_windows_payload, scan_windows


def scan(
    family: str | None = None,
    *,
    include_windows_update: bool = True,
    include_ignored: bool = False,
    categories: list[str] | None = None,
    older_than_days: int | None = None,
    fixture: Path | None = None,
) -> Report:
    if fixture:
        payload = json.loads(Path(fixture).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"fixture {fixture} is not a JSON object")
        report = report_from_windows_payload(
            payload, include_windows_update=include_windows_update
        )
        report.notes.append(f"fixture {Path(fixture).resolve()}")
    else:
        fam = (family or detect_family()).lower()
        if fam == "windows":
            report = scan_windows(include_windows_update=include_windows_update)
        elif fam == "linux":
            report = scan_linux()
        else:
            report = scan_linux()
            report.notes.append(f"Unknown OS family {fam!r}; attempted linux collect.")
    if not include_ignored:
        apply_ignore(report, load_ignored())
    apply_view_filters(report, categories=categories, older_than_days=older_than_days)
    return report
