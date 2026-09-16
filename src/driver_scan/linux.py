from __future__ import annotations

import re
from pathlib import Path

from driver_scan.classify import category_from_pci, category_from_usb_name, linux_mismatch
from driver_scan.models import Finding, Report, utc_now
from driver_scan.oem import apply_chassis, read_dmi
from driver_scan.util import detect_family, hostname, kernel, os_pretty, run, which
from driver_scan.vendors import official_url

# Bridges / chipset functions that often have no kernel driver and are not "missing".
SKIP_PCI_CLASSES = frozenset(
    {
        "0600",  # host bridge
        "0601",  # ISA bridge
        "0604",  # PCI-to-PCI bridge
        "0580",  # memory controller / PMC
    }
)

USB_SKIP_NAMES = ("root hub", "hub")
USB_HUB_IDS = frozenset(
    {
        "1d6b:0002",
        "1d6b:0003",
        "05e3:0610",
        "05e3:0608",
        "05e3:0620",
    }
)

PCI_LINE = re.compile(
    r"^(?P<slot>[0-9a-fA-F:.]+)\s+(?P<cls>.+?)\s+\[(?P<cc>[0-9a-fA-F]{4})\]:\s+(?P<rest>.+)$"
)
PCI_ID = re.compile(r"\[(?P<ven>[0-9a-fA-F]{4}):(?P<dev>[0-9a-fA-F]{4})\]")
USB_LINE = re.compile(
    r"^Bus\s+(?P<bus>\d+)\s+Device\s+(?P<dev>\d+):\s+ID\s+"
    r"(?P<ven>[0-9a-fA-F]{4}):(?P<prod>[0-9a-fA-F]{4})\s+(?P<name>.+)$"
)
FW_FAIL = re.compile(
    r"(Direct firmware load.{0,160}failed|"
    r"failed to (?:load|find) firmware|"
    r"request_firmware.{0,80}failed|"
    r"firmware: .{0,80}(?:not found|failed with error))",
    re.I,
)
PKG_HINT = re.compile(
    r"(firmware|microcode|nvidia|mesa|xserver-xorg-video|broadcom|rtl8|"
    r"iwlwifi|i915|displaylink|realtek)",
    re.I,
)


def scan_linux() -> Report:
    report = Report(
        hostname=hostname(),
        os=os_pretty(),
        kernel=kernel(),
        scanned_at=utc_now(),
        notes=[
            "Scan-only. Driver Scan does not download or install third-party driver packs.",
            "Use the OEM support page or the distro package manager for updates.",
        ],
    )
    if detect_family() != "linux":
        report.tools_skipped.append("linux-collect (not linux)")
        return report

    pci_out = _tool(report, "lspci", ["lspci", "-nnk"])
    if pci_out is not None:
        report.findings.extend(parse_lspci(pci_out))

    usb_out = _tool(report, "lsusb", ["lsusb"])
    usb_bind = _usb_sysfs_drivers()
    if usb_out is not None:
        report.findings.extend(parse_lsusb(usb_out, usb_bind))

    dmesg_out = _tool(report, "dmesg", ["dmesg", "--color=never"])
    if dmesg_out is not None:
        report.findings.extend(parse_firmware_log(dmesg_out, source="dmesg"))
    else:
        journal = _tool(
            report,
            "journalctl",
            ["journalctl", "-k", "-b", "--no-pager", "-g", "firmware", "-n", "80"],
        )
        if journal is not None:
            report.findings.extend(parse_firmware_log(journal, source="journalctl"))

    if which("dkms"):
        dkms_out = _tool(report, "dkms", ["dkms", "status"])
        if dkms_out is not None:
            report.findings.extend(parse_dkms(dkms_out))
    else:
        report.tools_skipped.append("dkms")

    if which("ubuntu-drivers"):
        ud = _tool(report, "ubuntu-drivers", ["ubuntu-drivers", "devices"])
        if ud is not None:
            report.findings.extend(parse_ubuntu_drivers(ud))
    else:
        report.tools_skipped.append("ubuntu-drivers")

    if which("apt-get") or which("apt"):
        apt = _tool(
            report,
            "apt",
            ["apt", "list", "--upgradable"],
            timeout=45,
        )
        if apt is not None:
            report.findings.extend(parse_apt_upgradable(apt))
    else:
        report.tools_skipped.append("apt")

    annotate_modinfo(report.findings)
    apply_chassis(report, *read_dmi())
    return report


def report_from_linux_payload(payload: dict) -> Report:
    """Build a report from recorded lspci/lsusb/dmesg/apt text (no live probes)."""
    report = Report(
        hostname=str(payload.get("hostname") or hostname()),
        os=str(payload.get("os") or os_pretty()),
        kernel=str(payload.get("kernel") or kernel()),
        scanned_at=utc_now(),
        notes=[
            "Scan-only. Driver Scan does not download or install third-party driver packs.",
            "Use the OEM support page or the distro package manager for updates.",
        ],
    )
    report.tools_used.append("linux-payload")
    lspci = payload.get("lspci")
    if isinstance(lspci, str) and lspci.strip():
        report.findings.extend(parse_lspci(lspci))
        report.tools_used.append("lspci")
    lsusb = payload.get("lsusb")
    if isinstance(lsusb, str) and lsusb.strip():
        bind = payload.get("usb_bind") or {}
        if not isinstance(bind, dict):
            bind = {}
        report.findings.extend(parse_lsusb(lsusb, {str(k): v for k, v in bind.items()}))
        report.tools_used.append("lsusb")
    dmesg = payload.get("dmesg") or payload.get("firmware_log")
    if isinstance(dmesg, str) and dmesg.strip():
        report.findings.extend(parse_firmware_log(dmesg, source="dmesg"))
        report.tools_used.append("dmesg")
    dkms = payload.get("dkms")
    if isinstance(dkms, str) and dkms.strip():
        report.findings.extend(parse_dkms(dkms))
        report.tools_used.append("dkms")
    ubuntu = payload.get("ubuntu_drivers")
    if isinstance(ubuntu, str) and ubuntu.strip():
        report.findings.extend(parse_ubuntu_drivers(ubuntu))
        report.tools_used.append("ubuntu-drivers")
    apt = payload.get("apt_upgradable")
    if isinstance(apt, str) and apt.strip():
        report.findings.extend(parse_apt_upgradable(apt))
        report.tools_used.append("apt")
    dnf = payload.get("dnf_upgradable") or payload.get("yum_upgradable")
    if isinstance(dnf, str) and dnf.strip():
        report.findings.extend(parse_dnf_upgradable(dnf))
        report.tools_used.append("dnf")
    versions = payload.get("modinfo") or {}
    if isinstance(versions, dict):
        for f in report.findings:
            if f.driver and versions.get(f.driver):
                f.version = str(versions[f.driver])
    apply_chassis(
        report,
        str(payload.get("manufacturer") or "") or None,
        str(payload.get("model") or "") or None,
        str(payload.get("serial") or "") or None,
    )
    return report


def _tool(report: Report, name: str, argv: list[str], timeout: int = 20) -> str | None:
    if not which(argv[0]):
        report.tools_skipped.append(name)
        return None
    code, out, err = run(argv, timeout=timeout)
    if code != 0 and not out.strip():
        report.tools_skipped.append(f"{name} (exit {code})")
        if err.strip():
            report.notes.append(f"{name}: {err.strip().splitlines()[0][:200]}")
        return None
    report.tools_used.append(name)
    return out


def parse_lspci(text: str) -> list[Finding]:
    findings: list[Finding] = []
    current: dict[str, str | list[str]] | None = None

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        findings.append(_pci_finding(current))
        current = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            continue
        m = PCI_LINE.match(line)
        if m:
            flush()
            rest = m.group("rest")
            ids = list(PCI_ID.finditer(rest))
            ven = ids[-1].group("ven").lower() if ids else None
            dev = ids[-1].group("dev").lower() if ids else None
            name = rest
            if ids:
                name = rest[: ids[-1].start()].strip()
            current = {
                "slot": m.group("slot"),
                "cls": m.group("cls"),
                "cc": m.group("cc").lower(),
                "name": name,
                "ven": ven or "",
                "dev": dev or "",
                "driver": "",
                "modules": [],
            }
            continue
        if current is None:
            continue
        if line.startswith("\tKernel driver in use:"):
            current["driver"] = line.split(":", 1)[1].strip()
        elif line.startswith("\tKernel modules:"):
            mods = [p.strip() for p in line.split(":", 1)[1].split(",") if p.strip()]
            current["modules"] = mods
    flush()
    return findings


def _pci_finding(cur: dict[str, str | list[str]]) -> Finding:
    slot = str(cur["slot"])
    cc = str(cur["cc"])
    ven = str(cur["ven"]) or None
    dev = str(cur["dev"]) or None
    name = str(cur["name"])
    driver = str(cur["driver"]) or None
    modules = list(cur["modules"]) if isinstance(cur["modules"], list) else []
    fid = f"pci:{slot}"
    url = official_url(ven, name)
    cat = category_from_pci(cc)
    skip = cc in SKIP_PCI_CLASSES
    if skip and not driver:
        return Finding(
            id=fid,
            severity="skip",
            bus="pci",
            name=f"{slot} {name}",
            detail=f"PCI class {cc} typically has no loadable driver.",
            vendor_id=ven,
            device_id=dev,
            modules=modules,
            official_url=url,
            category=cat,  # type: ignore[arg-type]
        )
    if driver:
        why = linux_mismatch(ven, driver, cat)
        if why:
            return Finding(
                id=fid,
                severity="mismatch",
                bus="pci",
                name=f"{slot} {name}",
                detail=why,
                vendor_id=ven,
                device_id=dev,
                driver=driver,
                modules=modules,
                official_url=url,
                category=cat,  # type: ignore[arg-type]
                suggested=[
                    "Install the vendor graphics stack from the distro or the GPU maker support page.",
                    f"Vendor page: {url}" if url else "Identify the GPU vendor support page.",
                ],
            )
        return Finding(
            id=fid,
            severity="ok",
            bus="pci",
            name=f"{slot} {name}",
            detail=f"Kernel driver in use: {driver}",
            vendor_id=ven,
            device_id=dev,
            driver=driver,
            modules=modules,
            official_url=url,
            category=cat,  # type: ignore[arg-type]
        )
    if modules:
        return Finding(
            id=fid,
            severity="missing",
            bus="pci",
            name=f"{slot} {name}",
            detail="Modules exist but no kernel driver is bound.",
            vendor_id=ven,
            device_id=dev,
            modules=modules,
            official_url=url,
            category=cat,  # type: ignore[arg-type]
            suggested=[
                f"sudo modprobe {modules[0]}",
                "Check dmesg for firmware load failures.",
                f"OEM / vendor page: {url}" if url else "Identify OEM support page from the chassis.",
            ],
        )
    return Finding(
        id=fid,
        severity="missing",
        bus="pci",
        name=f"{slot} {name}",
        detail="No kernel driver in use and no modules listed.",
        vendor_id=ven,
        device_id=dev,
        official_url=url,
        category=cat,  # type: ignore[arg-type]
        suggested=[
            "Search the OEM support page with the PCI ID "
            f"{ven}:{dev}" if ven and dev else "Search the OEM support page.",
            "On Debian/Ubuntu: apt search firmware / linux-firmware",
        ],
    )


def parse_lsusb(text: str, bound: dict[str, str | None]) -> list[Finding]:
    findings: list[Finding] = []
    for raw in text.splitlines():
        m = USB_LINE.match(raw.strip())
        if not m:
            continue
        ven = m.group("ven").lower()
        prod = m.group("prod").lower()
        vid = f"{ven}:{prod}"
        name = m.group("name").strip()
        busn = int(m.group("bus"))
        devn = int(m.group("dev"))
        key = f"{busn}:{devn}"
        driver = bound.get(key)
        fid = f"usb:{key}:{vid}"
        url = official_url(ven, name)
        cat = category_from_usb_name(name)
        skip = vid in USB_HUB_IDS or any(s in name.lower() for s in USB_SKIP_NAMES)
        if skip:
            findings.append(
                Finding(
                    id=fid,
                    severity="skip",
                    bus="usb",
                    name=name,
                    detail="USB hub / root hub.",
                    vendor_id=ven,
                    device_id=prod,
                    driver=driver,
                    official_url=url,
                    category=cat,  # type: ignore[arg-type]
                )
            )
            continue
        if driver:
            findings.append(
                Finding(
                    id=fid,
                    severity="ok",
                    bus="usb",
                    name=name,
                    detail=f"Bound USB driver: {driver}",
                    vendor_id=ven,
                    device_id=prod,
                    driver=driver,
                    official_url=url,
                    category=cat,  # type: ignore[arg-type]
                )
            )
            continue
        findings.append(
            Finding(
                id=fid,
                severity="missing",
                bus="usb",
                name=name,
                detail="Present on USB bus with no driver bound in sysfs.",
                vendor_id=ven,
                device_id=prod,
                official_url=url,
                category=cat,  # type: ignore[arg-type]
                suggested=[
                    f"Look up USB ID {vid} on the OEM or vendor support page.",
                    f"Vendor page: {url}" if url else "Identify the chassis OEM (Dell/HP/Lenovo) support site.",
                ],
            )
        )
    return findings


def _usb_sysfs_drivers() -> dict[str, str | None]:
    """Map 'busnum:devnum' -> driver name."""
    out: dict[str, str | None] = {}
    root = Path("/sys/bus/usb/devices")
    if not root.is_dir():
        return out
    for node in root.iterdir():
        vendor = node / "idVendor"
        if not vendor.exists():
            continue
        try:
            bus = int((node / "busnum").read_text().strip())
            dev = int((node / "devnum").read_text().strip())
        except (OSError, ValueError):
            continue
        driver_link = node / "driver"
        driver = None
        if driver_link.is_symlink():
            driver = driver_link.resolve().name
        out[f"{bus}:{dev}"] = driver
    return out


def parse_firmware_log(text: str, *, source: str) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        if not FW_FAIL.search(raw):
            continue
        line = raw.strip()
        key = line[-160:]
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            Finding(
                id=f"firmware:{len(findings)+1}",
                severity="firmware",
                bus="firmware",
                name="Firmware load failure",
                detail=f"{source}: {line[:300]}",
                suggested=[
                    "Debian/Ubuntu: sudo apt-get install linux-firmware firmware-misc-nonfree",
                    "Reboot after firmware packages change.",
                ],
            )
        )
    return findings


def parse_dkms(text: str) -> list[Finding]:
    findings: list[Finding] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        severity: str = "ok"
        if any(w in low for w in ("error", "broken", "installed-unbuilt", "failed")):
            severity = "error"
        findings.append(
            Finding(
                id=f"dkms:{line[:80]}",
                severity=severity,  # type: ignore[arg-type]
                bus="dkms",
                name="DKMS",
                detail=line,
                suggested=["sudo dkms autoinstall"] if severity == "error" else [],
            )
        )
    return findings


def parse_ubuntu_drivers(text: str) -> list[Finding]:
    findings: list[Finding] = []
    if not text.strip():
        return findings
    findings.append(
        Finding(
            id="ubuntu-drivers",
            severity="update",
            bus="package",
            name="ubuntu-drivers devices",
            detail=text.strip()[:1500],
            suggested=["sudo ubuntu-drivers autoinstall  # Ubuntu only, review first"],
        )
    )
    return findings


def parse_apt_package_names(text: str) -> list[str]:
    names: list[str] = []
    for raw in text.splitlines():
        pkg = raw.split("/", 1)[0].strip()
        if pkg and PKG_HINT.search(pkg) and pkg not in names:
            names.append(pkg)
    return names


def parse_apt_upgradable(text: str) -> list[Finding]:
    hits = [ln.strip() for ln in text.splitlines() if ln.strip() and PKG_HINT.search(ln.split("/", 1)[0])]
    if not hits:
        return []
    pkgs = parse_apt_package_names("\n".join(hits))
    return [
        Finding(
            id="apt:driver-firmware",
            severity="update",
            bus="package",
            name="OS packages with driver/firmware updates",
            detail="\n".join(hits[:40]),
            modules=pkgs,
            suggested=[
                "sudo apt-get update && sudo apt-get upgrade  # review the list first",
                "driver-scan fetch -o ./driver-downloads  # apt-get download those packages",
            ],
        )
    ]


def parse_dnf_upgradable(text: str) -> list[Finding]:
    hits: list[str] = []
    names: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("Obsoleting") or line.startswith("Last metadata"):
            continue
        pkg = line.split()[0].split(".")[0]
        if pkg and PKG_HINT.search(pkg):
            hits.append(line)
            if pkg not in names:
                names.append(pkg)
    if not hits:
        return []
    return [
        Finding(
            id="dnf:driver-firmware",
            severity="update",
            bus="package",
            name="OS packages with driver/firmware updates",
            detail="\n".join(hits[:40]),
            modules=names,
            suggested=["sudo dnf upgrade  # review the list first"],
        )
    ]


def annotate_modinfo(findings: list[Finding]) -> None:
    if not which("modinfo"):
        return
    cache: dict[str, str] = {}
    for f in findings:
        name = f.driver
        if not name:
            continue
        if name not in cache:
            code, out, _err = run(["modinfo", "-F", "version", name], timeout=5)
            cache[name] = out.strip() if code == 0 else ""
        if cache[name]:
            f.version = cache[name]
            if "version" not in f.detail.lower():
                f.detail = f"{f.detail} version {f.version}"
