#!/usr/bin/env python3
"""Replay RHEL 10.2 (newest GA Red Hat Enterprise Linux as of 2026-09) on this box."""

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

FIXTURE = Path(__file__).resolve().parent / "data" / "rhel-10.2-poweredge.json"


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
    parser.add_argument("--html", type=Path, default=ROOT / "tests" / "last-results-rhel102.html")
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
    expect(report.hostname == "rhel-102-sim", "hostname", failures)
    expect("Red Hat Enterprise Linux 10.2" in report.os, "os RHEL 10.2", failures)
    expect("el10_2" in report.kernel, "kernel el10_2", failures)
    expect(report.oem == "Dell", "chassis Dell", failures)
    expect(report.model == "PowerEdge R760", "model PowerEdge R760", failures)
    expect(counts.get("missing", 0) >= 1, "missing mlx5_core unbound", failures)
    expect(counts.get("mismatch", 0) >= 1, "nouveau mismatch", failures)
    expect(counts.get("firmware", 0) >= 1, "mlx5 firmware fail", failures)
    expect(counts.get("update", 0) >= 1, "dnf firmware/nvidia/mesa", failures)
    expect(counts.get("error", 0) >= 1, "dkms nvidia unbuilt", failures)
    by_id = {f.id: f for f in report.findings}
    mlx = by_id.get("pci:03:00.0")
    expect(mlx is not None and mlx.severity == "missing", "ConnectX missing", failures)
    nv = [f for f in report.findings if f.vendor_id == "10de"]
    expect(nv and nv[0].severity == "mismatch" and nv[0].driver == "nouveau", "NVIDIA A40 nouveau", failures)
    perc = by_id.get("pci:01:00.0")
    expect(perc is not None and perc.category == "storage" and perc.severity == "ok", "PERC storage ok", failures)
    dnf = next((f for f in report.findings if f.id == "dnf:driver-firmware"), None)
    expect(
        dnf is not None and "linux-firmware" in dnf.detail and "kmod-nvidia" in dnf.detail and "curl" not in dnf.detail,
        "dnf filter",
        failures,
    )
    ast = by_id.get("pci:00:02.0")
    expect(ast is not None and ast.driver == "ast" and ast.version == "1.14.0", "ASPEED ast version", failures)
    idrac = [f for f in report.findings if "iDRAC" in f.name]
    expect(idrac and idrac[0].severity == "missing", "iDRAC USB unbound", failures)

    html_path = args.html
    code, _out = run_cli(
        ["scan", "--fixture", str(fixture), "--include-ignored", "--html", "-o", str(html_path)]
    )
    expect(code == 1, "scan exit 1 because problems exist", failures)
    expect(html_path.is_file() and "rhel-102-sim" in html_path.read_text(), "html report", failures)

    code, out = run_cli(["scan", "--fixture", str(fixture), "--include-ignored", "--problems-only"])
    expect("nouveau" in out.lower() and "mlx5" in out.lower(), "problems-only text", failures)

    code, out = run_cli(["list", "--fixture", str(fixture), "--include-ignored", "--category", "storage"])
    expect("PERC" in out or "MegaRAID" in out, "list storage", failures)

    code, out = run_cli(["locate", "--fixture", str(fixture), "--include-ignored"])
    expect("dell.com" in out, "locate Dell OEM", failures)
    expect("nvidia.com" in out.lower(), "locate NVIDIA", failures)

    code, out = run_cli(["guide", "--fixture", str(fixture), "--include-ignored"])
    expect("backup" in out and "restore" in out, "guide playbook", failures)
    expect("update" in out, "guide updates", failures)

    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / "rhel102-backup.zip"
        with zipfile.ZipFile(zpath, "w") as zf:
            zf.writestr("modprobe.d/mlx5.conf", "options mlx5_core\n")
            zf.writestr("modules-load.d/nvidia.conf", "nvidia\n")
        code, out = run_cli(["restore", str(zpath), "--os", "linux", "--only", "mlx5"])
        expect("mlx5.conf" in out and "dry-run" in out, "restore --only mlx5", failures)
        expect("nvidia.conf" not in out, "restore --only excludes nvidia conf", failures)

    print(f"{len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
