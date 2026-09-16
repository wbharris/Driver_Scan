from driver_scan.cli import main
from driver_scan.models import Finding, Report
from driver_scan.report import render_json, render_markdown, render_text


def test_help_and_version(capsys):
    try:
        main(["--help"])
    except SystemExit as e:
        assert e.code == 0
    out = capsys.readouterr().out
    assert "Scan this machine" in out
    assert "backup" in out.lower()
    assert "schedule" in out.lower()
    assert "locate" in out.lower()
    assert "fetch" in out.lower()
    assert "restore" in out.lower()
    assert "guide" in out.lower()
    assert "list" in out.lower()
    assert "ignore" in out.lower()


def test_renderers():
    report = Report(
        hostname="box",
        os="Kali",
        kernel="7.1",
        scanned_at="2026-01-01T00:00:00Z",
        findings=[
            Finding(
                id="pci:1",
                severity="missing",
                bus="pci",
                name="Wi-Fi",
                detail="unbound",
                vendor_id="8086",
                device_id="24fd",
                official_url="https://www.intel.com/content/www/us/en/download-center/home.html",
            ),
            Finding(id="pci:2", severity="ok", bus="pci", name="GPU", detail="i915"),
        ],
        tools_used=["lspci"],
    )
    text = render_text(report, problems_only=True)
    assert "Wi-Fi" in text
    assert "GPU" not in text
    md = render_markdown(report)
    assert "# Driver Scan" in md
    assert "missing" in md
    js = render_json(report)
    assert '"problem_count": 1' in js
