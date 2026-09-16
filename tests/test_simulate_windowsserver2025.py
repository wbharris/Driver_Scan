from pathlib import Path

from driver_scan.scan import scan
from simulate_windowsserver2025 import FIXTURE, main as simulate_main


def test_server2025_fixture_inventory():
    report = scan(fixture=FIXTURE, include_ignored=True)
    assert report.hostname == "WIN-S2025SIM"
    assert "Windows Server 2025" in report.os
    assert report.kernel.startswith("10.0.26100")
    assert report.oem == "Dell"
    assert report.model == "PowerEdge R760"
    counts = report.counts()
    assert counts["missing"] >= 1
    assert counts["mismatch"] >= 2
    assert counts["error"] >= 1
    assert counts["update"] >= 2
    by = {f.name: f for f in report.findings}
    assert by["NVIDIA Mellanox ConnectX-6 Dx"].severity == "missing"
    assert by["Microsoft Basic Display Adapter"].severity == "mismatch"
    assert by["Dell 12Gbps SAS HBA"].severity == "mismatch"
    assert by["QLogic FastLinQ QL41232 25GbE"].severity == "error"
    assert by["PERC H755 Adapter"].category == "storage"


def test_simulate_server2025_harness(tmp_path, monkeypatch):
    html = tmp_path / "s2025.html"
    monkeypatch.setattr("sys.argv", ["simulate_windowsserver2025.py", "--html", str(html)])
    assert simulate_main() == 0
    assert html.is_file()
    text = html.read_text(encoding="utf-8")
    assert "WIN-S2025SIM" in text
    assert "Windows Server 2025" in text


def test_fixture_file_present():
    assert Path(FIXTURE).is_file()
