#!/usr/bin/env python3
"""Replay a Windows 11 collector payload on this Linux box and exercise the CLI."""

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

FIXTURE = Path(__file__).resolve().parent / "data" / "windows11-dell.json"


def expect(ok: bool, label: str, failures: list[str]) -> None:
    print(("PASS" if ok else "FAIL"), label)
    if not ok:
        failures.append(label)


def run_cli(argv: list[str]) -> tuple[int, str]:
    from io import StringIO
    from contextlib import redirect_stdout, redirect_stderr

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
    parser.add_argument("--html", type=Path, default=ROOT / "tests" / "last-results.html")
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
    expect(report.hostname == "DESKTOP-W11SIM", "hostname", failures)
    expect("Windows 11" in report.os, "os Windows 11", failures)
    expect(report.oem == "Dell", "chassis Dell", failures)
    expect(report.model == "XPS 15 9530", "model XPS 15 9530", failures)
    expect(counts.get("missing", 0) >= 1, "missing webcam", failures)
    expect(counts.get("mismatch", 0) >= 2, "mismatch Basic Display + code 48", failures)
    expect(counts.get("error", 0) >= 1, "error code 43", failures)
    expect(counts.get("update", 0) >= 2, "Windows Update driver offers", failures)
    expect(counts.get("skip", 0) >= 1, "disabled Bluetooth skip", failures)
    names = {f.name: f for f in report.findings}
    expect(names["Integrated Webcam HD"].category == "imaging", "webcam imaging", failures)
    expect(names["HP LaserJet Pro M404dn"].category == "printer", "printer class", failures)
    expect(names["Microsoft Basic Display Adapter"].severity == "mismatch", "basic display", failures)
    expect(names["Intel(R) Ethernet Connection I219-LM"].driver_date == "2019-08-15", "old NIC date", failures)

    html_path = args.html
    code, _out = run_cli(
        ["scan", "--fixture", str(fixture), "--include-ignored", "--html", "-o", str(html_path)]
    )
    expect(code == 1, "scan exit 1 because problems exist", failures)
    expect(html_path.is_file() and "DESKTOP-W11SIM" in html_path.read_text(), "html report", failures)

    code, out = run_cli(["scan", "--fixture", str(fixture), "--include-ignored", "--problems-only"])
    expect("missing" in out and "mismatch" in out, "problems-only text", failures)

    code, out = run_cli(["list", "--fixture", str(fixture), "--include-ignored", "--category", "graphics"])
    expect("Iris" in out and "Basic Display" in out, "list graphics", failures)

    code, out = run_cli(["list", "--fixture", str(fixture), "--include-ignored", "--older-than", "365"])
    expect("I219-LM" in out, "older-than 365d includes 2019 NIC", failures)

    code, out = run_cli(["locate", "--fixture", str(fixture), "--include-ignored"])
    expect("dell.com" in out and "nvidia.com" in out.lower(), "locate OEM + NVIDIA", failures)

    code, out = run_cli(["guide", "--fixture", str(fixture), "--include-ignored"])
    expect("backup" in out and "mismatch" in out and "restore" in out, "guide playbook", failures)

    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "w11-backup.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("drivers/display/nv_disp.inf", "[Version]\nSignature=\"$WINDOWS NT$\"\n")
            zf.writestr("drivers/net/netwtw08.inf", "[Version]\nSignature=\"$WINDOWS NT$\"\n")
        code, out = run_cli(["restore", str(zpath), "--os", "windows", "--only", "display"])
        expect("nv_disp.inf" in out and "dry-run" in out, "restore --only display dry-run", failures)
        expect("netwtw08.inf" not in out, "restore --only excludes other INF", failures)

    print(f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
