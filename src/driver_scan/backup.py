from __future__ import annotations

import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from driver_scan.report import render_json, render_markdown
from driver_scan.scan import scan
from driver_scan.util import detect_family, hostname, powershell_exe, run, which


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


def _windows_restore_point(description: str) -> list[str]:
    exe = powershell_exe()
    if not exe:
        return ["no powershell; skipped System Restore point"]
    code, out, err = run(
        [
            exe,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            f'Checkpoint-Computer -Description "{description}" -RestorePointType MODIFY_SETTINGS',
        ],
        timeout=90,
    )
    if code == 0:
        return [f"Windows restore point: {description}"]
    return [f"restore point skipped: {(err or out).strip().splitlines()[:1] or code}"]


def restore(
    archive: Path,
    *,
    apply: bool = False,
    dest_root: Path | None = None,
    family: str | None = None,
    only: str | None = None,
) -> list[str]:
    archive = archive.expanduser().resolve()
    if not archive.is_file():
        return [f"not a file: {archive}"]
    fam = (family or detect_family()).lower()
    notes: list[str] = [f"archive {archive}"]
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        infs = [n for n in names if n.lower().endswith(".inf") and n.startswith("drivers/")]
        confs = [n for n in names if n.startswith("modprobe.d/") or n.startswith("modules-load.d/")]
        if only:
            infs = [n for n in infs if only.lower() in n.lower()]
            confs = [n for n in confs if only.lower() in n.lower()]
            notes.append(f"filter --only {only!r}: {len(infs)} inf / {len(confs)} configs")
        if fam == "windows":
            notes.extend(_restore_windows(zf, infs, apply=apply))
        else:
            notes.extend(_restore_linux(zf, confs, apply=apply, dest_root=dest_root))
    return notes


def _restore_windows(zf: zipfile.ZipFile, infs: list[str], *, apply: bool) -> list[str]:
    notes = [f"{len(infs)} INF files in archive"]
    if not infs:
        notes.append("no drivers/*.inf in zip; nothing to restore")
        return notes
    if not apply:
        notes.append("dry-run; pass --apply as Administrator to pnputil /add-driver")
        notes.extend(infs[:20])
        return notes
    notes.extend(_windows_restore_point("Driver Scan restore"))
    pnputil = which("pnputil") or which("pnputil.exe")
    if not pnputil:
        notes.append("pnputil not found")
        return notes
    extract_root = Path(tempfile.mkdtemp(prefix="driver-scan-restore-"))
    wanted = _windows_extract_members(zf.namelist(), infs)
    notes.extend(extract_zip_members(zf, wanted, extract_root))
    for inf in infs:
        rel = zip_member_relpath(inf)
        if rel is None:
            notes.append(f"skipped unsafe INF path {inf!r}")
            continue
        code, out, err = run(
            [pnputil, "/add-driver", str(extract_root / rel), "/install"],
            timeout=180,
        )
        notes.append(f"{inf}: {(out or err).strip() or f'exit {code}'}")
    return notes


def _restore_linux(
    zf: zipfile.ZipFile,
    confs: list[str],
    *,
    apply: bool,
    dest_root: Path | None,
) -> list[str]:
    notes = [f"{len(confs)} config files in archive"]
    mapping = {
        "modprobe.d/": Path("/etc/modprobe.d"),
        "modules-load.d/": Path("/etc/modules-load.d"),
    }
    if dest_root is not None:
        mapping = {
            "modprobe.d/": dest_root / "modprobe.d",
            "modules-load.d/": dest_root / "modules-load.d",
        }
    if not confs:
        notes.append("no modprobe.d / modules-load.d in zip; kernel modules are not in the backup")
        return notes
    if not apply:
        notes.append("dry-run; pass --apply to copy configs (does not reinstall kernel modules)")
        notes.extend(confs[:20])
        return notes
    for name in confs:
        rel = zip_member_relpath(name)
        if rel is None or len(rel.parts) != 2:
            notes.append(f"skipped unsafe zip member {name!r}")
            continue
        prefix = rel.parts[0] + "/"
        dest_dir = mapping.get(prefix)
        if dest_dir is None:
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = (dest_dir / rel.name).resolve()
        dest_root_res = dest_dir.resolve()
        if not _is_under(target, dest_root_res):
            notes.append(f"skipped zip slip {name!r}")
            continue
        target.write_bytes(zf.read(name))
        notes.append(f"wrote {target}")
    return notes


def zip_member_relpath(name: str) -> Path | None:
    """Return a relative path for a zip member, or None if it is unsafe."""
    raw = name.replace("\\", "/").strip()
    if not raw or raw.endswith("/"):
        return None
    if raw.startswith("/") or raw.startswith("../") or raw == "..":
        return None
    if len(raw) >= 2 and raw[1] == ":":
        return None
    parts: list[str] = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == ".." or part.startswith(".."):
            return None
        parts.append(part)
    if not parts:
        return None
    return Path(*parts)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _windows_extract_members(all_names: list[str], infs: list[str]) -> list[str]:
    """Selected INFs plus other files in the same zip directory (sys/cat next to inf)."""
    parents: set[str] = set()
    selected: set[str] = set()
    for inf in infs:
        rel = zip_member_relpath(inf)
        if rel is None:
            continue
        selected.add(inf.replace("\\", "/"))
        parent = rel.parent.as_posix()
        if parent != ".":
            parents.add(parent)
    out: list[str] = []
    for name in all_names:
        rel = zip_member_relpath(name)
        if rel is None:
            continue
        n = name.replace("\\", "/")
        parent = rel.parent.as_posix()
        if n in selected or parent in parents:
            out.append(name)
    return out


def extract_zip_members(zf: zipfile.ZipFile, names: list[str], dest: Path) -> list[str]:
    notes: list[str] = []
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    for name in names:
        rel = zip_member_relpath(name)
        if rel is None:
            notes.append(f"skipped unsafe zip member {name!r}")
            continue
        target = (dest / rel).resolve()
        if not _is_under(target, dest):
            notes.append(f"skipped zip slip {name!r}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(name) as src:
            target.write_bytes(src.read())
        notes.append(f"extracted {rel.as_posix()}")
    return notes
