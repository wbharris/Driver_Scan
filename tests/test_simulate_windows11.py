from pathlib import Path

from driver_scan.scan import scan
from simulate_windows11 import FIXTURE, main as simulate_main


def test_windows11_fixture_inventory():
    report = scan(fixture=FIXTURE, include_ignored=True)
    assert report.hostname == "DESKTOP-W11SIM"
    assert "Windows 11" in report.os
    assert report.oem == "Dell"
    counts = report.counts()
    assert counts["missing"] >= 1
    assert counts["mismatch"] >= 2
    assert counts["error"] >= 1
    assert counts["update"] >= 2
    by = {f.name: f for f in report.findings}
    assert by["Integrated Webcam HD"].severity == "missing"
    assert by["Microsoft Basic Display Adapter"].severity == "mismatch"
    assert by["Synaptics SMBus TouchPad"].severity == "mismatch"
    assert by["NVIDIA USB Type-C Port Policy Controller"].severity == "error"
    assert by["HP LaserJet Pro M404dn"].category == "printer"


def test_simulate_windows11_harness(tmp_path, monkeypatch):
    html = tmp_path / "w11.html"
    monkeypatch.setattr("sys.argv", ["simulate_windows11.py", "--html", str(html)])
    assert simulate_main() == 0
    assert html.is_file()
    assert "DESKTOP-W11SIM" in html.read_text(encoding="utf-8")


def test_fixture_file_present():
    assert Path(FIXTURE).is_file()
