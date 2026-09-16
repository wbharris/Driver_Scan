from driver_scan.fetch import fetch
from driver_scan.models import Finding, Report


def test_fetch_uses_dnf_when_apt_missing(tmp_path, monkeypatch):
    report = Report(
        hostname="rhel",
        os="Red Hat Enterprise Linux 10.2",
        kernel="6.12",
        scanned_at="2026-01-01T00:00:00Z",
        findings=[
            Finding(
                id="dnf:driver-firmware",
                severity="update",
                bus="package",
                name="OS packages",
                detail="linux-firmware.noarch 1",
                modules=["linux-firmware"],
            )
        ],
    )
    monkeypatch.setattr("driver_scan.fetch.scan", lambda *a, **k: report)
    monkeypatch.setattr("driver_scan.fetch.detect_family", lambda: "linux")
    monkeypatch.setattr(
        "driver_scan.fetch.which",
        lambda name: "/usr/bin/dnf" if name == "dnf" else None,
    )
    calls = []

    def fake_run(argv, timeout=180, cwd=None):
        calls.append(argv)
        return 0, "ok", ""

    monkeypatch.setattr("driver_scan.fetch.run", fake_run)
    dest, notes = fetch(tmp_path / "dl")
    assert (dest / "LINKS.txt").is_file()
    assert any("downloaded linux-firmware" in n for n in notes)
    assert any(argv[0].endswith("dnf") and "download" in argv for argv in calls)
