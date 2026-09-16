from __future__ import annotations

from driver_scan.models import PROBLEM_SEVERITIES, Report

PLAYBOOK = (
    "missing",
    "mismatch",
    "error",
    "firmware",
    "update",
)


def guide_text(report: Report) -> str:
    lines = [
        "Driver Scan guide",
        f"{report.hostname}  {report.os}  problems={len(report.problems())}",
        "",
        "1. Snapshot first:  driver-scan backup -o ./drivers.zip",
        "2. Prefer OS updates (Windows Update optional drivers, or apt) before vendor sites.",
    ]
    n = 3
    if report.oem_url:
        lines.append(f"{n}. PC maker: {report.oem_url}")
        n += 1
    by: dict[str, list[str]] = {k: [] for k in PLAYBOOK}
    for f in report.findings:
        if f.severity not in PROBLEM_SEVERITIES:
            continue
        ident = f"{f.vendor_id}:{f.device_id}" if f.vendor_id and f.device_id else f.bus
        url = f.official_url or report.oem_url or ""
        by.setdefault(f.severity, []).append(f"   - [{f.category}] {f.name} ({ident}) {url}".rstrip())
    for sev in PLAYBOOK:
        rows = by.get(sev) or []
        if not rows:
            continue
        lines.append(f"{n}. {sev} ({len(rows)})")
        lines.extend(rows[:20])
        n += 1
    lines.append(f"{n}. Re-scan:  driver-scan --problems-only")
    n += 1
    lines.append(f"{n}. If the new driver is worse:  driver-scan restore ./drivers.zip")
    lines.append("")
    lines.append("This guide does not install software. Review each official page before you apply it.")
    return "\n".join(lines) + "\n"
