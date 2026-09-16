from __future__ import annotations

import json

from driver_scan.models import PROBLEM_SEVERITIES, Finding, Report

ORDER = ("missing", "error", "firmware", "update", "ok", "skip")


def render_markdown(report: Report, *, problems_only: bool = False) -> str:
    findings = report.problems() if problems_only else report.findings
    findings = sorted(findings, key=lambda f: (ORDER.index(f.severity) if f.severity in ORDER else 9, f.id))
    counts = report.counts()
    lines = [
        "# Driver Scan",
        "",
        f"- **Host:** {report.hostname}",
        f"- **OS:** {report.os}",
        f"- **Kernel:** {report.kernel}",
        f"- **When:** {report.scanned_at}",
        f"- **Problems:** {len(report.problems())}",
        "",
        "## Counts",
        "",
        "| Severity | Count |",
        "|----------|------:|",
    ]
    for key in ORDER:
        if key in counts:
            lines.append(f"| {key} | {counts[key]} |")
    for key, n in sorted(counts.items()):
        if key not in ORDER:
            lines.append(f"| {key} | {n} |")
    lines += ["", "## Tools", ""]
    if report.tools_used:
        lines.append("Used: " + ", ".join(report.tools_used))
    if report.tools_skipped:
        lines.append("Skipped: " + ", ".join(report.tools_skipped))
    if report.notes:
        lines += ["", "## Notes", ""]
        for n in report.notes:
            lines.append(f"- {n}")
    lines += ["", "## Findings", ""]
    if not findings:
        lines.append("No matching findings.")
        return "\n".join(lines) + "\n"
    for f in findings:
        lines.append(_finding_md(f))
    return "\n".join(lines) + "\n"


def _finding_md(f: Finding) -> str:
    bits = [f"### `{f.severity}` {f.name}", "", f"{f.detail}", ""]
    meta = []
    if f.vendor_id and f.device_id:
        meta.append(f"id `{f.vendor_id}:{f.device_id}`")
    if f.driver:
        meta.append(f"driver `{f.driver}`")
    if f.modules:
        meta.append("modules " + ", ".join(f"`{m}`" for m in f.modules))
    if f.official_url:
        meta.append(f"[official source]({f.official_url})")
    if meta:
        bits.append("- " + " · ".join(meta))
        bits.append("")
    if f.suggested:
        bits.append("Next:")
        for s in f.suggested:
            bits.append(f"- {s}")
        bits.append("")
    return "\n".join(bits)


def render_text(report: Report, *, problems_only: bool = False) -> str:
    findings = report.problems() if problems_only else report.findings
    findings = sorted(findings, key=lambda f: (ORDER.index(f.severity) if f.severity in ORDER else 9, f.id))
    counts = report.counts()
    count_s = " ".join(f"{k}={v}" for k, v in counts.items() if v)
    lines = [
        f"Driver Scan  {report.hostname}  {report.os}  {report.kernel}",
        f"scanned {report.scanned_at}  problems={len(report.problems())}  {count_s}",
        "",
    ]
    show = [f for f in findings if f.severity in PROBLEM_SEVERITIES] if problems_only else findings
    if problems_only:
        show = findings
    problems = [f for f in show if f.severity in PROBLEM_SEVERITIES]
    if not problems and problems_only:
        lines.append("No missing, error, firmware, or update findings.")
        return "\n".join(lines) + "\n"
    for f in show:
        if problems_only and f.severity not in PROBLEM_SEVERITIES:
            continue
        ident = f"{f.vendor_id}:{f.device_id}" if f.vendor_id and f.device_id else f.bus
        drv = f.driver or ("unbound" if f.severity == "missing" else "-")
        lines.append(f"[{f.severity:8}] {f.name}  ({ident})  {drv}")
        if f.detail and f.severity in PROBLEM_SEVERITIES:
            for dl in f.detail.splitlines()[:4]:
                lines.append(f"           {dl}")
        if f.official_url and f.severity in PROBLEM_SEVERITIES:
            lines.append(f"           {f.official_url}")
    if report.tools_skipped:
        lines.append("")
        lines.append("skipped: " + ", ".join(report.tools_skipped))
    return "\n".join(lines) + "\n"


def render_json(report: Report, *, problems_only: bool = False) -> str:
    data = report.to_dict()
    if problems_only:
        data["findings"] = [f.to_dict() for f in report.problems()]
    return json.dumps(data, indent=2) + "\n"
