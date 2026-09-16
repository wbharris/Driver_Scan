from __future__ import annotations

import json

from driver_scan.models import PROBLEM_SEVERITIES, Finding, Report

ORDER = ("missing", "error", "mismatch", "firmware", "update", "ok", "skip")
CAT_ORDER = ("graphics", "audio", "network", "storage", "chipset", "usb", "other")


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
        f"- **Chassis:** {report.oem or '-'} {report.model or ''}".rstrip(),
        f"- **Problems:** {len(report.problems())}",
    ]
    if report.oem_url:
        lines.append(f"- **PC maker:** {report.oem_url}")
    lines += [
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
    if f.version:
        meta.append(f"version `{f.version}`")
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
    ]
    if report.oem or report.model:
        lines.append(f"chassis {report.oem or '-'} {report.model or ''}  {report.oem_url or ''}".rstrip())
    lines += [
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


def render_html(report: Report, *, problems_only: bool = False) -> str:
    findings = report.problems() if problems_only else report.findings
    findings = sorted(findings, key=lambda f: (ORDER.index(f.severity) if f.severity in ORDER else 9, f.id))
    rows = []
    for f in findings:
        url = f'<a href="{_esc(f.official_url)}">{_esc(f.official_url)}</a>' if f.official_url else ""
        ident = f"{f.vendor_id}:{f.device_id}" if f.vendor_id and f.device_id else f.bus
        rows.append(
            "<tr>"
            f"<td class='s {_esc(f.severity)}'>{_esc(f.severity)}</td>"
            f"<td>{_esc(f.category)}</td>"
            f"<td>{_esc(f.name)}</td>"
            f"<td>{_esc(ident)}</td>"
            f"<td>{_esc(f.driver or '')} {_esc(f.version or '')}</td>"
            f"<td>{_esc(f.detail.splitlines()[0] if f.detail else '')}</td>"
            f"<td>{url}</td>"
            "</tr>"
        )
    counts = " ".join(f"{k}={v}" for k, v in report.counts().items() if v)
    chassis = _esc(" ".join(p for p in (report.oem, report.model) if p) or "-")
    oem = (
        f'<p>PC maker: <a href="{_esc(report.oem_url)}">{_esc(report.oem_url)}</a></p>'
        if report.oem_url
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Driver Scan — {_esc(report.hostname)}</title>
<style>
body {{ font: 14px/1.4 system-ui, sans-serif; background:#0d1117; color:#e6edf3; margin:24px; }}
table {{ border-collapse: collapse; width:100%; }}
th, td {{ border-bottom:1px solid #30363d; padding:6px 8px; text-align:left; vertical-align:top; }}
th {{ color:#8b949e; font-weight:600; }}
.s.missing,.s.error,.s.firmware,.s.mismatch {{ color:#f85149; }}
.s.update {{ color:#d29922; }}
.s.ok {{ color:#3fb950; }}
.s.skip {{ color:#8b949e; }}
a {{ color:#58a6ff; }}
</style></head><body>
<h1>Driver Scan</h1>
<p>{_esc(report.hostname)} — {_esc(report.os)} — {_esc(report.kernel)}</p>
<p>scanned {_esc(report.scanned_at)} — problems={len(report.problems())} — { _esc(counts) }</p>
<p>chassis {chassis}</p>
{oem}
<table><thead><tr><th>Status</th><th>Class</th><th>Device</th><th>Id</th><th>Driver</th><th>Detail</th><th>Official</th></tr></thead>
<tbody>
{''.join(rows) or '<tr><td colspan="7">No matching findings.</td></tr>'}
</tbody></table>
</body></html>
"""


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
