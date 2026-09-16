import zipfile

from driver_scan.backup import backup, restore
from driver_scan.guide import guide_text
from driver_scan.fetch import locate_text
from driver_scan.linux import parse_apt_package_names
from driver_scan.models import Finding, Report
from driver_scan.report import render_html
from driver_scan.schedule import write_runner_script
from driver_scan.vendors import oem_from_text


def test_oem_from_chassis_text():
    label, url = oem_from_text("Dell Inc. Latitude")
    assert label == "Dell"
    assert url and "dell.com" in url


def test_locate_and_html():
    report = Report(
        hostname="box",
        os="Kali",
        kernel="7",
        scanned_at="2026-01-01T00:00:00Z",
        oem="Dell",
        model="Latitude",
        oem_url="https://www.dell.com/support/home",
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
            )
        ],
    )
    loc = locate_text(report)
    assert "dell.com" in loc
    assert "intel.com" in loc
    html = render_html(report)
    assert "Wi-Fi" in html
    assert "missing" in html


def test_apt_package_names():
    names = parse_apt_package_names(
        "linux-firmware/kali 1 amd64 [upgradable from: 0]\ncurl/kali 1 amd64 [upgradable from: 0]\n"
    )
    assert names == ["linux-firmware"]


def test_backup_zip(tmp_path):
    dest = tmp_path / "b.zip"
    path, _notes = backup(dest)
    assert path.exists()
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    assert "report.json" in names
    assert "report.md" in names


def test_schedule_runner(tmp_path, monkeypatch):
    monkeypatch.setattr("driver_scan.schedule.data_dir", lambda: tmp_path)
    script = write_runner_script(do_backup=True, notify=False)
    text = script.read_text(encoding="utf-8")
    assert "scan" in text
    assert "backup" in text
    assert str(tmp_path) in text


def test_restore_dry_run(tmp_path):
    archive = tmp_path / "b.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("modprobe.d/example.conf", b"blacklist foo\n")
    notes = restore(archive, apply=False, family="linux")
    blob = "\n".join(notes)
    assert "dry-run" in blob
    assert "modprobe.d/example.conf" in blob
    applied = restore(archive, apply=True, family="linux", dest_root=tmp_path / "etc")
    assert (tmp_path / "etc" / "modprobe.d" / "example.conf").read_text() == "blacklist foo\n"
    assert any("wrote" in n for n in applied)


def test_guide_lists_backup_then_restore():
    report = Report(
        hostname="box",
        os="Kali",
        kernel="7",
        scanned_at="2026-01-01T00:00:00Z",
        oem_url="https://www.dell.com/support/home",
        findings=[
            Finding(
                id="pci:1",
                severity="mismatch",
                bus="pci",
                name="GPU",
                detail="nouveau",
                category="graphics",
                official_url="https://www.nvidia.com/Download/index.aspx",
            )
        ],
    )
    text = guide_text(report)
    assert "backup" in text
    assert "mismatch" in text
    assert "restore" in text
