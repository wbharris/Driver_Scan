import json

from driver_scan.cli import main
from driver_scan.redact import redact_obj


def test_redact_serial_keys():
    data = {
        "hostname": "LAT5490",
        "serial": "ABC123",
        "manufacturer": "Dell Inc.",
        "nested": {"serialNumber": "XYZ"},
    }
    out = redact_obj(data)
    assert out["serial"] == "REDACTED"
    assert out["nested"]["serialNumber"] == "REDACTED"
    assert out["hostname"] == "LAT5490"


def test_redact_cli_and_scan_mkdir(tmp_path):
    src = tmp_path / "dell-live.json"
    src.write_text(json.dumps({"serial": "SECRET", "devices": []}), encoding="utf-8")
    dest = tmp_path / "redacted.json"
    assert main(["redact", str(src), "-o", str(dest)]) == 0
    assert json.loads(dest.read_text())["serial"] == "REDACTED"
    html = tmp_path / "cases" / "out.html"
    assert main(["scan", "--fixture", str(dest), "--include-ignored", "--html", "-o", str(html)]) in (0, 1)
    assert html.is_file()
