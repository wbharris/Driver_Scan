from __future__ import annotations

from pathlib import Path

from driver_scan.linux import parse_apt_package_names
from driver_scan.models import Report
from driver_scan.scan import scan
from driver_scan.util import detect_family, run, which


def locate_text(report: Report) -> str:
    lines = []
    if report.oem or report.model:
        lines.append(f"chassis: {report.oem or '-'} {report.model or ''}".rstrip())
        if report.serial:
            lines.append(f"serial: {report.serial}")
        if report.oem_url:
            lines.append(f"pc-maker: {report.oem_url}")
        lines.append("")
    seen: set[str] = set()
    for f in report.problems():
        url = f.official_url
        if not url or url in seen:
            continue
        seen.add(url)
        ident = f"{f.vendor_id}:{f.device_id}" if f.vendor_id and f.device_id else f.id
        lines.append(f"{f.severity:8} {f.name}  ({ident})")
        lines.append(f"         {url}")
    if not seen:
        lines.append("No official locate URLs on problem findings.")
    return "\n".join(lines).rstrip() + "\n"


def fetch(dest: Path, *, family: str | None = None, include_windows_update: bool = True) -> tuple[Path, list[str]]:
    dest = dest.expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)
    report = scan(family, include_windows_update=include_windows_update)
    notes: list[str] = []
    (dest / "LINKS.txt").write_text(locate_text(report), encoding="utf-8")
    notes.append(f"wrote {dest / 'LINKS.txt'}")
    fam = (family or detect_family()).lower()
    if fam == "linux":
        notes.extend(_fetch_linux(dest, report))
    else:
        notes.append(
            "Windows: use Windows Update optional driver updates; "
            "LINKS.txt has PC-maker and chip-vendor pages. No third-party packs."
        )
    return dest, notes


def _packages_from_report(report: Report) -> list[str]:
    packages: list[str] = []
    for f in report.findings:
        if f.id in {"apt:driver-firmware", "dnf:driver-firmware"}:
            packages = list(f.modules) or parse_apt_package_names(f.detail)
    return packages


def _fetch_linux(dest: Path, report: Report) -> list[str]:
    notes: list[str] = []
    packages = _packages_from_report(report)
    if not packages:
        notes.append("no driver/firmware OS packages to download")
        return notes
    apt_get = which("apt-get")
    dnf = which("dnf")
    if apt_get:
        for pkg in packages:
            code, out, err = run([apt_get, "download", pkg], timeout=180, cwd=dest)
            if code == 0:
                notes.append(f"downloaded {pkg}")
            else:
                notes.append(f"apt-get download {pkg} exit {code}: {(err or out).strip().splitlines()[:1]}")
        return notes
    if dnf:
        for pkg in packages:
            code, out, err = run(
                [dnf, "download", f"--destdir={dest}", pkg],
                timeout=180,
                cwd=dest,
            )
            if code == 0:
                notes.append(f"downloaded {pkg}")
            else:
                notes.append(f"dnf download {pkg} exit {code}: {(err or out).strip().splitlines()[:1]}")
        return notes
    notes.append("apt-get/dnf not found")
    return notes
