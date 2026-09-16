from pathlib import Path

from driver_scan.linux import parse_dnf_upgradable
from driver_scan.scan import scan
from simulate_rhel102 import FIXTURE, main as simulate_main


def test_dnf_package_filter():
    findings = parse_dnf_upgradable(
        "linux-firmware.noarch 1.el10 updates\ncurl.x86_64 8.0 baseos\nkmod-nvidia.x86_64 580 appstream\n"
    )
    assert findings and findings[0].severity == "update"
    assert "linux-firmware" in findings[0].detail
    assert "kmod-nvidia" in findings[0].detail
    assert "curl" not in findings[0].detail


def test_rhel102_fixture_inventory():
    report = scan(fixture=FIXTURE, include_ignored=True)
    assert report.hostname == "rhel-102-sim"
    assert "Red Hat Enterprise Linux 10.2" in report.os
    assert "el10_2" in report.kernel
    assert report.oem == "Dell"
    counts = report.counts()
    assert counts.get("missing", 0) >= 1
    assert counts.get("mismatch", 0) >= 1
    assert counts.get("firmware", 0) >= 1
    assert counts.get("update", 0) >= 1
    assert counts.get("error", 0) >= 1
    nv = [f for f in report.findings if f.vendor_id == "10de"]
    assert nv and nv[0].driver == "nouveau"


def test_simulate_rhel102_harness(tmp_path, monkeypatch):
    html = tmp_path / "rhel102.html"
    monkeypatch.setattr("sys.argv", ["simulate_rhel102.py", "--html", str(html)])
    assert simulate_main() == 0
    text = html.read_text(encoding="utf-8")
    assert "rhel-102-sim" in text
    assert "Red Hat Enterprise Linux 10.2" in text


def test_fixture_file_present():
    assert Path(FIXTURE).is_file()
