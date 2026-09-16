from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from driver_scan.classify import category_from_pnp, windows_mismatch
from driver_scan.models import Finding, Report, utc_now
from driver_scan.oem import apply_chassis
from driver_scan.util import detect_family, hostname, kernel, os_pretty, powershell_exe, run
from driver_scan.vendors import official_url

# ConfigManagerErrorCode — https://learn.microsoft.com/windows-hardware/drivers/install/device-manager-error-messages
CM_MISSING = frozenset({28})  # CM_PROB_FAILED_INSTALL — no driver
CM_ERROR = frozenset({1, 10, 14, 18, 19, 21, 24, 29, 31, 37, 39, 43, 52})
CM_SKIP = frozenset({22, 45})  # disabled / not connected

COLLECTOR = Path(__file__).with_name("windows_collect.ps1")


def mark_incomplete(report: Report, reason: str) -> None:
    if report.incomplete:
        return
    report.incomplete = True
    if "windows-pnp" not in report.tools_skipped:
        report.tools_skipped.append("windows-pnp")
    report.findings.append(
        Finding(
            id="collect:incomplete",
            severity="error",
            bus="system",
            name="Incomplete inventory",
            detail=reason,
            suggested=["Re-run the scan; do not treat an empty report as a clean machine."],
        )
    )


def scan_windows(*, include_windows_update: bool = True) -> Report:
    if detect_family() != "windows":
        report = Report(
            hostname=hostname(),
            os=os_pretty(),
            kernel=kernel(),
            scanned_at=utc_now(),
            notes=[
                "Scan-only. Driver Scan does not download or install third-party driver packs.",
                "Prefer Windows Update, then the PC maker (Dell/HP/Lenovo), then the chip vendor.",
            ],
        )
        report.tools_skipped.append("windows-collect (not windows)")
        return report

    payload, skipped = collect_windows(include_windows_update=include_windows_update)
    report = report_from_windows_payload(payload or {}, include_windows_update=include_windows_update)
    report.tools_skipped.extend(skipped)
    if payload is None:
        report.notes.append("windows collect returned no payload")
        mark_incomplete(report, "Windows collector returned no payload.")
    return report


def report_from_windows_payload(
    payload: dict[str, Any],
    *,
    include_windows_update: bool = True,
) -> Report:
    report = Report(
        hostname=str(payload.get("hostname") or hostname()),
        os=str(payload.get("os") or os_pretty()),
        kernel=str(payload.get("kernel") or kernel()),
        scanned_at=utc_now(),
        notes=[
            "Scan-only. Driver Scan does not download or install third-party driver packs.",
            "Prefer Windows Update, then the PC maker (Dell/HP/Lenovo), then the chip vendor.",
        ],
    )
    findings = findings_from_windows_payload(payload)
    if not include_windows_update:
        findings = [f for f in findings if not str(f.id).startswith("wu:")]
    report.findings.extend(findings)
    report.tools_used.append("windows-payload")
    errors = [str(item) for item in (payload.get("collectErrors") or [])]
    for item in errors:
        report.notes.append(f"collector: {item[:300]}")
    pnp_failed = any("Win32_PnPEntity" in item for item in errors)
    if pnp_failed or (not payload.get("devices") and errors):
        mark_incomplete(report, "; ".join(errors)[:500] or "PnP inventory was not collected.")
    if payload.get("windowsUpdateError"):
        report.notes.append(str(payload["windowsUpdateError"])[:300])
        report.tools_skipped.append("windows-update-search")
    elif include_windows_update and any(str(f.id).startswith("wu:") for f in findings):
        report.tools_used.append("windows-update-search")
    apply_chassis(
        report,
        str(payload.get("manufacturer") or "") or None,
        str(payload.get("model") or "") or None,
        str(payload.get("serial") or "") or None,
    )
    return report


def collect_windows(*, include_windows_update: bool = True) -> tuple[dict[str, Any] | None, list[str]]:
    skipped: list[str] = []
    exe = powershell_exe()
    if not exe:
        skipped.append("powershell")
        return None, skipped
    if not COLLECTOR.exists():
        skipped.append("windows_collect.ps1")
        return None, skipped
    argv = [
        exe,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(COLLECTOR),
    ]
    if include_windows_update:
        argv.append("-IncludeWindowsUpdate")
    code, out, err = run(argv, timeout=180)
    raw = out.strip()
    if raw and not raw.startswith("{"):
        brace = raw.find("{")
        if brace >= 0:
            raw = raw[brace:]
    if not raw:
        skipped.append(f"powershell collect (exit {code})")
        if err.strip():
            skipped.append(err.strip().splitlines()[0][:200])
        return None, skipped
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        skipped.append("powershell JSON parse")
        if code != 0:
            skipped.append(f"powershell collect (exit {code})")
        return None, skipped
    if code != 0:
        skipped.append(f"powershell collect (exit {code}, JSON kept)")
    if not isinstance(data, dict):
        skipped.append("powershell JSON shape")
        return None, skipped
    return data, skipped


def findings_from_windows_payload(data: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    drivers = data.get("signedDrivers") or []
    by_id: dict[str, dict[str, Any]] = {}
    for d in drivers:
        if not isinstance(d, dict):
            continue
        did = str(d.get("deviceId") or "").upper()
        if did:
            by_id[did] = d

    for dev in data.get("devices") or []:
        if not isinstance(dev, dict):
            continue
        findings.append(_device_finding(dev, by_id))

    for upd in data.get("windowsUpdateDrivers") or []:
        if not isinstance(upd, dict):
            continue
        title = str(upd.get("title") or "Windows Update driver")
        findings.append(
            Finding(
                id=f"wu:{title[:80]}",
                severity="update",
                bus="package",
                name=title,
                detail=str(upd.get("description") or "Driver update offered by Windows Update."),
                official_url="https://support.microsoft.com/windows",
                suggested=[
                    "Settings → Windows Update → Advanced options → Optional updates",
                    "Or: usoclient StartInteractiveScan  (review before installing)",
                ],
            )
        )
    return findings


def _device_finding(dev: dict[str, Any], signed: dict[str, dict[str, Any]]) -> Finding:
    instance = str(dev.get("instanceId") or dev.get("deviceId") or "unknown")
    name = str(dev.get("name") or instance)
    manufacturer = str(dev.get("manufacturer") or "")
    status = str(dev.get("status") or "")
    try:
        code = int(dev.get("configManagerErrorCode") or 0)
    except (TypeError, ValueError):
        code = 0
    problem = str(dev.get("problem") or "")
    class_name = str(dev.get("class") or "")
    vid = _hw_id_piece(instance, "VEN_") or _hw_id_piece(instance, "VID_")
    did = _hw_id_piece(instance, "DEV_") or _hw_id_piece(instance, "PID_")
    url = official_url(vid, f"{manufacturer} {name}")
    cat = category_from_pnp(class_name, name)
    signed_row = signed.get(instance.upper())
    driver = None
    extra = ""
    version = None
    driver_date = None
    if signed_row:
        driver = str(signed_row.get("infName") or "") or None
        ver = signed_row.get("driverVersion")
        date = signed_row.get("driverDate")
        extra = f" Signed driver {ver or '?'} ({date or 'no date'})."
        version = str(ver) if ver else None
        driver_date = str(date)[:10] if date else None

    present = dev.get("present")
    why = windows_mismatch(name=name, class_name=class_name, code=code, category=cat)
    if present in (False, 0, "False", "false"):
        severity = "skip"
        detail = "Device not present (unplugged / not enumerated)."
        suggested = []
    elif code in CM_MISSING or (status.lower() == "error" and code == 28):
        severity = "missing"
        detail = f"Device Manager code {code} (no driver). {problem} {status}".strip()
        suggested = [
            "Windows Update optional driver updates",
            f"OEM support: {url}" if url else "PC maker support page (Dell/HP/Lenovo/…)",
        ]
    elif code in CM_SKIP:
        severity = "skip"
        detail = f"Code {code} ({problem or status}). Not treated as missing."
        suggested = []
    elif why:
        severity = "mismatch"
        detail = why + extra
        suggested = [
            "Windows Update optional driver updates",
            f"GPU/chip vendor page: {url}" if url else "PC maker support page",
        ]
    elif code in CM_ERROR or status.lower() in {"error", "degraded"}:
        severity = "error"
        detail = f"Device Manager code {code}: {problem or status}.{extra}"
        suggested = [
            "Device Manager → device → Update driver → Search automatically",
            f"OEM support: {url}" if url else "PC maker support page",
        ]
    else:
        severity = "ok"
        detail = f"{class_name or 'PnP'} {status or 'OK'}.{extra}".strip()
        suggested = []

    return Finding(
        id=f"pnp:{instance}",
        severity=severity,  # type: ignore[arg-type]
        bus="pnp",
        name=name,
        detail=detail.strip(),
        vendor_id=vid.lower() if vid else None,
        device_id=did.lower() if did else None,
        driver=driver,
        version=version,
        driver_date=driver_date,
        official_url=url,
        category=cat,  # type: ignore[arg-type]
        suggested=suggested,
    )


def _hw_id_piece(instance: str, prefix: str) -> str | None:
    up = instance.upper()
    idx = up.find(prefix)
    if idx < 0:
        return None
    start = idx + len(prefix)
    chunk = up[start : start + 8]
    hexpart = "".join(c for c in chunk if c in "0123456789ABCDEF")
    if len(hexpart) >= 4:
        return hexpart[:4]
    return None
