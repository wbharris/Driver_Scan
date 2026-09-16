from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

from driver_scan.report import render_json, render_markdown
from driver_scan.scan import scan
from driver_scan.util import detect_family, hostname, run, which


def backup(dest: Path | None = None, *, family: str | None = None) -> tuple[Path, list[str]]:
    notes: list[str] = []
    report = scan(family)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = dest or Path(f"driver-scan-backup-{hostname()}-{stamp}.zip")
    dest = dest.expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    staging: dict[str, bytes] = {
        "report.json": render_json(report).encode("utf-8"),
        "report.md": render_markdown(report).encode("utf-8"),
    }
    fam = (family or detect_family()).lower()
    if fam == "linux":
        _linux_files(staging, notes)
    elif fam == "windows":
        _windows_export(dest.parent / f".driver-scan-export-{stamp}", staging, notes)

    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in staging.items():
            zf.writestr(name, data)
    notes.append(f"wrote {dest}")
    return dest, notes


def _linux_files(staging: dict[str, bytes], notes: list[str]) -> None:
    for label, argv in (
        ("lspci.txt", ["lspci", "-nnk"]),
        ("lsusb.txt", ["lsusb"]),
        ("dkms-status.txt", ["dkms", "status"]),
    ):
        if not which(argv[0]):
            notes.append(f"skipped {argv[0]}")
            continue
        code, out, err = run(argv)
        staging[label] = (out or err).encode("utf-8", errors="replace")
        if code != 0:
            notes.append(f"{argv[0]} exit {code}")
    for folder, prefix in (
        (Path("/etc/modprobe.d"), "modprobe.d"),
        (Path("/etc/modules-load.d"), "modules-load.d"),
    ):
        if not folder.is_dir():
            continue
        for path in sorted(folder.iterdir()):
            if path.is_file():
                try:
                    staging[f"{prefix}/{path.name}"] = path.read_bytes()
                except OSError as exc:
                    notes.append(f"skip {path}: {exc}")


def _windows_export(folder: Path, staging: dict[str, bytes], notes: list[str]) -> None:
    pnputil = which("pnputil") or which("pnputil.exe")
    if not pnputil:
        notes.append("pnputil not found; zip contains the scan report only")
        return
    folder.mkdir(parents=True, exist_ok=True)
    code, out, err = run([pnputil, "/export-driver", "*", str(folder)], timeout=180)
    staging["pnputil-export.txt"] = (out + "\n" + err).encode("utf-8", errors="replace")
    if code != 0:
        notes.append(f"pnputil export exit {code} (often needs Administrator)")
        return
    for path in folder.rglob("*"):
        if path.is_file():
            rel = path.relative_to(folder).as_posix()
            staging[f"drivers/{rel}"] = path.read_bytes()
    notes.append("exported Windows driver store via pnputil")
