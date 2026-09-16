#!/usr/bin/env python3
"""Replay Ubuntu 26.04.1 LTS (newest released Ubuntu as of 2026-09) on this box."""

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

FIXTURE = Path(__file__).resolve().parent / "data" / "ubuntu-26.04.1-xps.json"


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
    parser.add_argument("--html", type=Path, default=ROOT / "tests" / "last-results-ubuntu2604.html")
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
    expect(report.hostname == "ubuntu-2604-sim", "hostname", failures)
    expect("Ubuntu 26.04.1" in report.os, "os Ubuntu 26.04.1 LTS", failures)
    expect(report.kernel.startswith("7.0.0"), "kernel 7.0", failures)
    expect(report.oem == "Dell", "chassis Dell", failures)
    expect(report.model == "XPS 15 9530", "model XPS 15 9530", failures)
    expect(counts.get("missing", 0) >= 1, "missing iwlwifi unbound", failures)
    expect(counts.get("mismatch", 0) >= 1, "nouveau mismatch", failures)
    expect(counts.get("firmware", 0) >= 1, "iwlwifi firmware fail", failures)
    expect(counts.get("update", 0) >= 2, "ubuntu-drivers + apt firmware/mesa/nvidia", failures)
    expect(counts.get("error", 0) >= 1, "dkms nvidia unbuilt", failures)
    by_id = {f.id: f for f in report.findings}
    names = {f.name: f for f in report.findings}
    wifi = by_id.get("pci:02:00.0")
    expect(wifi is not None and wifi.severity == "missing", "wifi PCI missing", failures)
    nv = [f for f in report.findings if f.vendor_id == "10de"]
    expect(nv and nv[0].severity == "mismatch" and nv[0].driver == "nouveau", "NVIDIA nouveau", failures)
    expect(any("Webcam" in f.name and f.category == "imaging" for f in report.findings), "webcam imaging", failures)
    expect(any(f.id == "ubuntu-drivers" for f in report.findings), "ubuntu-drivers row", failures)
    apt = next((f for f in report.findings if f.id == "apt:driver-firmware"), None)
    expect(apt is not None and "linux-firmware" in apt.detail and "curl" not in apt.detail, "apt filter", failures)
    iris = by_id.get("pci:00:02.0")
    expect(iris is not None and iris.severity == "ok" and iris.version == "1.6.0", "i915 version from fixture", failures)

    html_path = args.html
    code, _out = run_cli(
        ["scan", "--fixture", str(fixture), "--include-ignored", "--html", "-o", str(html_path)]
    )
    expect(code == 1, "scan exit 1 because problems exist", failures)
    expect(html_path.is_file() and "ubuntu-2604-sim" in html_path.read_text(), "html report", failures)

    code, out = run_cli(["scan", "--fixture", str(fixture), "--include-ignored", "--problems-only"])
    expect("nouveau" in out.lower() and "iwlwifi" in out.lower(), "problems-only text", failures)

    code, out = run_cli(["list", "--fixture", str(fixture), "--include-ignored", "--category", "graphics"])
    expect("Iris" in out and "nouveau" in out, "list graphics", failures)

    code, out = run_cli(["locate", "--fixture", str(fixture), "--include-ignored"])
    expect("dell.com" in out and "nvidia.com" in out.lower(), "locate Dell + NVIDIA", failures)

    code, out = run_cli(["guide", "--fixture", str(fixture), "--include-ignored"])
    expect("backup" in out and "restore" in out, "guide playbook", failures)
    expect("nvidia-driver-580" in out or "ubuntu-drivers" in out, "guide nvidia", failures)

    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "u2604-backup.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("modprobe.d/nvidia-blacklist.conf", "blacklist nouveau\n")
            zf.writestr("modules-load.d/nvidia.conf", "nvidia\n")
        code, out = run_cli(["restore", str(zpath), "--os", "linux", "--only", "nvidia-blacklist"])
        expect("nvidia-blacklist.conf" in out and "dry-run" in out, "restore --only nvidia-blacklist", failures)
        expect("modules-load.d/nvidia.conf" not in out, "restore --only excludes other conf", failures)

    print(f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
