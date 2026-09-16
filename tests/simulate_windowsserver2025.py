#!/usr/bin/env python3
"""Replay Windows Server 2025 (current LTSC, build 26100.33451) on this Linux box."""

from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from driver_scan.cli import main as cli_main  # noqa: E402
from driver_scan.scan import scan  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "data" / "windowsserver2025-poweredge.json"


def expect(ok: bool, label: str, failures: list[str]) -> None:
    print(("PASS" if ok else "FAIL"), label)
    if not ok:
        failures.append(label)


def run_cli(argv: list[str]) -> tuple[int, str]:
    from contextlib import redirect_stderr, redirect_stdout
    from io import StringIO

    buf = StringIO()
    err = StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(err):
            code = cli_main(argv)
    except SystemExit as exc:
        code = int(exc.code or 0)
    return code, buf.getvalue() + err.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=ROOT / "tests" / "last-results-server2025.html")
    args = parser.parse_args()
    failures: list[str] = []

    fixture = FIXTURE
    expect(fixture.is_file(), f"fixture exists {fixture}", failures)

    report = scan(fixture=fixture, include_ignored=True)
    counts = report.counts()
    print(
        f"host={report.hostname} os={report.os} kernel={report.kernel} "
        f"oem={report.oem} {report.model} problems={len(report.problems())} {counts}"
    )
    expect(report.hostname == "WIN-S2025SIM", "hostname", failures)
    expect("Windows Server 2025" in report.os, "os Server 2025", failures)
    expect(report.kernel.startswith("10.0.26100"), "kernel 26100", failures)
    expect(report.oem == "Dell", "chassis Dell", failures)
    expect(report.model == "PowerEdge R760", "model PowerEdge R760", failures)
    expect(counts.get("missing", 0) >= 1, "missing ConnectX-6", failures)
    expect(counts.get("mismatch", 0) >= 2, "mismatch Basic Display + SAS code 48", failures)
    expect(counts.get("error", 0) >= 1, "error QLogic code 43", failures)
    expect(counts.get("update", 0) >= 2, "Windows Update driver offers", failures)
    expect(counts.get("skip", 0) >= 1, "disabled iDRAC NDIS skip", failures)
    names = {f.name: f for f in report.findings}
    expect(names["NVIDIA Mellanox ConnectX-6 Dx"].severity == "missing", "ConnectX missing", failures)
    expect(names["NVIDIA Mellanox ConnectX-6 Dx"].category == "network", "ConnectX network", failures)
    expect(names["Microsoft Basic Display Adapter"].severity == "mismatch", "basic display", failures)
    expect(names["Dell 12Gbps SAS HBA"].severity == "mismatch", "SAS mismatch", failures)
    expect(names["QLogic FastLinQ QL41232 25GbE"].severity == "error", "QLogic error", failures)
    expect(names["PERC H755 Adapter"].category == "storage", "PERC storage", failures)
    expect(names["Broadcom NetXtreme E-Series BCM57414 10Gb"].driver_date == "2018-11-02", "old NIC date", failures)

    html_path = args.html
    code, _out = run_cli(
        ["scan", "--fixture", str(fixture), "--include-ignored", "--html", "-o", str(html_path)]
    )
    expect(code == 1, "scan exit 1 because problems exist", failures)
    expect(html_path.is_file() and "WIN-S2025SIM" in html_path.read_text(), "html report", failures)

    code, out = run_cli(["scan", "--fixture", str(fixture), "--include-ignored", "--problems-only"])
    expect("ConnectX" in out and "mismatch" in out, "problems-only text", failures)

    code, out = run_cli(["list", "--fixture", str(fixture), "--include-ignored", "--category", "storage"])
    expect("PERC H755" in out and "SAS HBA" in out, "list storage", failures)

    code, out = run_cli(["list", "--fixture", str(fixture), "--include-ignored", "--older-than", "365"])
    expect("BCM57414" in out, "older-than 365d includes 2018 Broadcom", failures)

    code, out = run_cli(["locate", "--fixture", str(fixture), "--include-ignored"])
    expect("dell.com" in out, "locate Dell OEM", failures)
    expect("nvidia.com" in out.lower(), "locate NVIDIA/Mellanox", failures)

    code, out = run_cli(["guide", "--fixture", str(fixture), "--include-ignored"])
    expect("backup" in out and "restore" in out, "guide playbook", failures)
    expect("dell.com" in out, "guide OEM", failures)

    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "s2025-backup.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("drivers/storage/lsi_sas3i.inf", "[Version]\nSignature=\"$WINDOWS NT$\"\n")
            zf.writestr("drivers/net/bxnd.inf", "[Version]\nSignature=\"$WINDOWS NT$\"\n")
        code, out = run_cli(["restore", str(zpath), "--os", "windows", "--only", "storage"])
        expect("lsi_sas3i.inf" in out and "dry-run" in out, "restore --only storage dry-run", failures)
        expect("bxnd.inf" not in out, "restore --only excludes NIC INF", failures)

    print(f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
