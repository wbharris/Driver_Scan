import zipfile
from pathlib import Path

from driver_scan.backup import backup, extract_zip_members, restore, zip_member_relpath
from driver_scan.filters import apply_view_filters
from driver_scan.guide import guide_text
from driver_scan.ignore import add_ignore, apply_ignore, is_ignored, load_ignored
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


def test_ignore_roundtrip(tmp_path):
    path = tmp_path / "ignore.txt"
    add_ignore("pci:02:00.0", path)
    add_ignore("8086:24fd", path)
    assert load_ignored(path) == ["8086:24fd", "pci:02:00.0"]
    report = Report(
        hostname="box",
        os="Kali",
        kernel="7",
        scanned_at="2026-01-01T00:00:00Z",
        findings=[
            Finding(id="pci:02:00.0", severity="missing", bus="pci", name="Wi-Fi", detail="unbound"),
        ],
    )
    assert apply_ignore(report, load_ignored(path)) == 1
    assert report.findings[0].severity == "skip"


def test_older_than_and_category_filters():
    report = Report(
        hostname="box",
        os="Kali",
        kernel="7",
        scanned_at="2026-01-01T00:00:00Z",
        findings=[
            Finding(
                id="a",
                severity="ok",
                bus="pnp",
                name="old gpu",
                detail="x",
                category="graphics",
                driver_date="2018-01-01",
            ),
            Finding(
                id="b",
                severity="ok",
                bus="pnp",
                name="new gpu",
                detail="x",
                category="graphics",
                driver_date="2026-09-01",
            ),
            Finding(id="c", severity="ok", bus="pnp", name="nic", detail="x", category="network"),
        ],
    )
    apply_view_filters(report, categories=["graphics"], older_than_days=365)
    assert [f.id for f in report.findings] == ["a"]


def test_older_than_zero_keeps_dated_drivers():
    report = Report(
        hostname="box",
        os="Kali",
        kernel="7",
        scanned_at="2026-01-01T00:00:00Z",
        findings=[
            Finding(
                id="dated",
                severity="ok",
                bus="pnp",
                name="nic",
                detail="x",
                driver_date="2019-08-15",
            ),
            Finding(id="undated", severity="ok", bus="pnp", name="hub", detail="x"),
        ],
    )
    apply_view_filters(report, older_than_days=0)
    assert [f.id for f in report.findings] == ["dated"]


def test_older_than_negative_rejected():
    report = Report(
        hostname="box",
        os="Kali",
        kernel="7",
        scanned_at="2026-01-01T00:00:00Z",
        findings=[],
    )
    try:
        apply_view_filters(report, older_than_days=-1)
    except ValueError as exc:
        assert ">= 0" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_ignore_is_exact_not_substring():
    wifi = Finding(id="pci:02:00.0", severity="missing", bus="pci", name="Wi-Fi", detail="x")
    other = Finding(id="pci:00:02.0", severity="ok", bus="pci", name="GPU", detail="x")
    assert is_ignored(wifi, ["pci:02:00.0"])
    assert not is_ignored(other, ["pci:0"])
    assert not is_ignored(wifi, ["pci:0"])
    vid = Finding(
        id="pnp:x",
        severity="missing",
        bus="pnp",
        name="cam",
        detail="x",
        vendor_id="1bcf",
        device_id="2b96",
    )
    assert is_ignored(vid, ["1BCF:2B96"])


def test_zip_slip_members_rejected(tmp_path):
    assert zip_member_relpath("../etc/passwd") is None
    assert zip_member_relpath("drivers/../evil.inf") is None
    assert zip_member_relpath("/tmp/x.inf") is None
    assert zip_member_relpath("drivers/net/foo.inf") == Path("drivers/net/foo.inf")
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../outside.inf", b"nope")
        zf.writestr("drivers/ok.inf", b"ok")
        zf.writestr("modprobe.d/../../tmp/evil.conf", b"nope")
    dest = tmp_path / "out"
    with zipfile.ZipFile(archive) as zf:
        notes = extract_zip_members(zf, zf.namelist(), dest)
    blob = "\n".join(notes)
    assert "unsafe" in blob
    assert (dest / "drivers" / "ok.inf").read_bytes() == b"ok"
    assert not (tmp_path / "outside.inf").exists()
    linux_notes = restore(archive, apply=True, family="linux", dest_root=tmp_path / "etc")
    assert any("unsafe" in n for n in linux_notes)
    assert not list((tmp_path / "etc").rglob("evil.conf")) if (tmp_path / "etc").exists() else True
