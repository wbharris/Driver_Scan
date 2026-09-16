from driver_scan.windows import findings_from_windows_payload


PAYLOAD = {
    "devices": [
        {
            "name": "Network Camera",
            "manufacturer": "Contoso",
            "status": "Error",
            "class": "Camera",
            "instanceId": r"USB\VID_1BCF&PID_2B96\5&123",
            "configManagerErrorCode": 28,
            "problem": "CM_PROB_FAILED_INSTALL",
        },
        {
            "name": "Intel(R) HD Graphics 520",
            "manufacturer": "Intel",
            "status": "OK",
            "class": "Display",
            "instanceId": r"PCI\VEN_8086&DEV_1916&SUBSYS_07A71028",
            "configManagerErrorCode": 0,
        },
        {
            "name": "Microsoft Basic Display Adapter",
            "manufacturer": "Microsoft",
            "status": "OK",
            "class": "Display",
            "instanceId": r"PCI\VEN_10DE&DEV_1CB3",
            "configManagerErrorCode": 0,
        },
        {
            "name": "Disabled NIC",
            "manufacturer": "Intel",
            "status": "Error",
            "class": "Net",
            "instanceId": r"PCI\VEN_8086&DEV_15D7",
            "configManagerErrorCode": 22,
        },
    ],
    "signedDrivers": [
        {
            "deviceId": r"PCI\VEN_8086&DEV_1916&SUBSYS_07A71028",
            "driverVersion": "31.0.101.0",
            "driverDate": "2024-01-01T00:00:00",
            "infName": "iigd_dch.inf",
        }
    ],
    "windowsUpdateDrivers": [
        {"title": "Intel - Net - 12.18.9.0", "description": "Intel Wireless"}
    ],
}


def test_windows_payload_severities():
    findings = findings_from_windows_payload(PAYLOAD)
    by_name = {f.name: f for f in findings}
    cam = by_name["Network Camera"]
    assert cam.severity == "missing"
    assert cam.vendor_id == "1bcf"
    assert cam.device_id == "2b96"
    gfx = by_name["Intel(R) HD Graphics 520"]
    assert gfx.severity == "ok"
    assert gfx.driver == "iigd_dch.inf"
    assert gfx.official_url
    assert by_name["Disabled NIC"].severity == "skip"
    assert by_name["Microsoft Basic Display Adapter"].severity == "mismatch"
    assert by_name["Microsoft Basic Display Adapter"].category == "graphics"
    wu = [f for f in findings if f.severity == "update"]
    assert wu and "Intel - Net" in wu[0].name
