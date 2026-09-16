from pathlib import Path

from driver_scan.scan import scan
from simulate_ubuntu2604 import FIXTURE, main as simulate_main


def test_ubuntu2604_fixture_inventory():
    report = scan(fixture=FIXTURE, include_ignored=True)
    assert report.hostname == "ubuntu-2604-sim"
    assert "Ubuntu 26.04.1" in report.os
    assert report.kernel.startswith("7.0.0")
    assert report.oem == "Dell"
    counts = report.counts()
    assert counts.get("missing", 0) >= 1
    assert counts.get("mismatch", 0) >= 1
    assert counts.get("firmware", 0) >= 1
    assert counts.get("update", 0) >= 2
    assert counts.get("error", 0) >= 1
    by_id = {f.id: f for f in report.findings}
    assert by_id["pci:02:00.0"].severity == "missing"
    nv = [f for f in report.findings if f.vendor_id == "10de"]
    assert nv and nv[0].driver == "nouveau" and nv[0].severity == "mismatch"
    apt = next(f for f in report.findings if f.id == "apt:driver-firmware")
    assert "linux-firmware" in apt.detail
    assert "curl" not in apt.detail


def test_simulate_ubuntu2604_harness(tmp_path, monkeypatch):
    html = tmp_path / "u2604.html"
    monkeypatch.setattr("sys.argv", ["simulate_ubuntu2604.py", "--html", str(html)])
    assert simulate_main() == 0
    text = html.read_text(encoding="utf-8")
    assert "ubuntu-2604-sim" in text
    assert "Ubuntu 26.04.1" in text


def test_fixture_file_present():
    assert Path(FIXTURE).is_file()
