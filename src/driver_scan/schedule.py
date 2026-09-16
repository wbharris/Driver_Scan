from __future__ import annotations

import sys
from pathlib import Path

from driver_scan.util import data_dir, detect_family, run, which

TASK_NAME = "DriverScan"


def runner_cmd() -> list[str]:
    exe = which("driver-scan")
    if exe:
        return [exe]
    return [sys.executable, "-m", "driver_scan"]


def write_runner_script(*, do_backup: bool, notify: bool) -> Path:
    root = data_dir()
    report = root / "last.txt"
    backup_zip = root / "last-backup.zip"
    cmd = runner_cmd()
    scan_line = _shell_join(cmd + ["scan", "--problems-only", "-o", str(report)])
    backup_line = _shell_join(cmd + ["backup", "-o", str(backup_zip)])
    if detect_family() == "windows":
        path = root / "run.cmd"
        lines = [
            "@echo off",
            "setlocal",
            "set STATUS=0",
            scan_line,
            "set STATUS=%ERRORLEVEL%",
            "if %STATUS% GTR 1 exit /b %STATUS%",
        ]
        if do_backup:
            lines.append(backup_line)
        lines.append("exit /b %STATUS%")
        path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        return path
    path = root / "run.sh"
    # Scan exits 1 when problems exist; that must not skip backup/notify.
    lines = [
        "#!/bin/sh",
        "set -e",
        "status=0",
        "set +e",
        scan_line,
        "status=$?",
        "set -e",
        'if [ "$status" -gt 1 ]; then exit "$status"; fi',
    ]
    if do_backup:
        lines.append(backup_line)
    if notify and which("notify-send"):
        lines.append(
            f'if grep -Eq "problems=[1-9][0-9]*" "{report}" 2>/dev/null; then '
            f'notify-send "Driver Scan" "Problems written to {report}"; fi'
        )
    lines.append('exit "$status"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def install(*, every: str, do_backup: bool, notify: bool) -> str:
    script = write_runner_script(do_backup=do_backup, notify=notify)
    cal = {"hourly": "hourly", "daily": "daily", "weekly": "weekly"}.get(every, "daily")
    if detect_family() == "windows":
        return _install_windows(script, cal)
    return _install_linux(script, cal)


def remove() -> str:
    if detect_family() == "windows":
        code, out, err = run(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"])
        return (out or err).strip() or f"schtasks delete exit {code}"
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    for name in ("driver-scan.timer", "driver-scan.service"):
        (unit_dir / name).unlink(missing_ok=True)
    run(["systemctl", "--user", "disable", "--now", "driver-scan.timer"])
    run(["systemctl", "--user", "daemon-reload"])
    return "removed systemd --user driver-scan.timer"


def status() -> str:
    if detect_family() == "windows":
        code, out, err = run(["schtasks", "/Query", "/TN", TASK_NAME, "/FO", "LIST", "/V"])
        return (out or err).strip() or f"schtasks query exit {code}"
    code, out, err = run(["systemctl", "--user", "status", "driver-scan.timer", "--no-pager"])
    return (out or err).strip() or f"systemctl exit {code}"


def _install_linux(script: Path, cal: str) -> str:
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    oncal = {"hourly": "hourly", "daily": "daily", "weekly": "weekly"}[cal]
    (unit_dir / "driver-scan.service").write_text(
        "[Unit]\nDescription=Driver Scan inventory\n\n"
        f"[Service]\nType=oneshot\nExecStart={script}\n",
        encoding="utf-8",
    )
    (unit_dir / "driver-scan.timer").write_text(
        "[Unit]\nDescription=Driver Scan schedule\n\n"
        f"[Timer]\nOnCalendar={oncal}\nPersistent=true\n\n"
        "[Install]\nWantedBy=timers.target\n",
        encoding="utf-8",
    )
    run(["systemctl", "--user", "daemon-reload"])
    code, out, err = run(["systemctl", "--user", "enable", "--now", "driver-scan.timer"])
    if code != 0:
        return f"wrote {unit_dir}/driver-scan.timer; enable failed: {(err or out).strip()}"
    return f"enabled systemd --user driver-scan.timer ({oncal}) -> {script}"


def _install_windows(script: Path, cal: str) -> str:
    sc = {"hourly": "HOURLY", "daily": "DAILY", "weekly": "WEEKLY"}[cal]
    argv = [
        "schtasks",
        "/Create",
        "/TN",
        TASK_NAME,
        "/TR",
        str(script),
        "/SC",
        sc,
        "/F",
    ]
    code, out, err = run(argv)
    if code != 0:
        return f"schtasks failed: {(err or out).strip()}"
    return f"scheduled {TASK_NAME} {sc} -> {script}"


def _shell_join(parts: list[str]) -> str:
    out = []
    for p in parts:
        if any(c.isspace() for c in p) or any(c in p for c in '"&|<>'):
            out.append('"' + p.replace('"', '\\"') + '"')
        else:
            out.append(p)
    return " ".join(out)
