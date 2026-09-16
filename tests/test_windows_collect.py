import json
from pathlib import Path

from driver_scan.windows import collect_windows, report_from_windows_payload


def test_collect_parses_json_after_warning(tmp_path, monkeypatch):
    script = tmp_path / "windows_collect.ps1"
    script.write_text("# dummy\n", encoding="utf-8")
    payload = {"hostname": "WIN", "devices": [], "signedDrivers": []}
    monkeypatch.setattr("driver_scan.windows.powershell_exe", lambda: "/bin/true")
    monkeypatch.setattr("driver_scan.windows.COLLECTOR", script)

    def fake_run(argv, timeout=180):
        return 0, "CIM warning\n" + json.dumps(payload), ""

    monkeypatch.setattr("driver_scan.windows.run", fake_run)
    data, skipped = collect_windows(include_windows_update=False)
    assert data["hostname"] == "WIN"
    assert skipped == []


def test_collect_keeps_json_on_nonzero_exit(tmp_path, monkeypatch):
    script = tmp_path / "windows_collect.ps1"
    script.write_text("# dummy\n", encoding="utf-8")
    payload = {"hostname": "WIN", "devices": [], "signedDrivers": []}
    monkeypatch.setattr("driver_scan.windows.powershell_exe", lambda: "/bin/true")
    monkeypatch.setattr("driver_scan.windows.COLLECTOR", script)

    def fake_run(argv, timeout=180):
        return 1, json.dumps(payload), "WU COM failed"

    monkeypatch.setattr("driver_scan.windows.run", fake_run)
    data, skipped = collect_windows()
    assert data["hostname"] == "WIN"
    assert any("exit 1" in s for s in skipped)


def test_collect_errors_land_on_report():
    report = report_from_windows_payload(
        {
            "hostname": "WIN",
            "os": "Microsoft Windows 11 Pro",
            "kernel": "10.0.26100",
            "devices": [],
            "signedDrivers": [],
            "collectErrors": ["Win32_PnPEntity: access denied"],
        }
    )
    assert any("access denied" in n for n in report.notes)
