from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path


def which(name: str) -> str | None:
    return shutil.which(name)


def run(
    argv: list[str],
    *,
    timeout: int = 30,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(cwd) if cwd else None,
            check=False,
        )
    except FileNotFoundError:
        return 127, "", f"not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(argv)}"
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def detect_family() -> str:
    sysname = platform.system().lower()
    if sysname == "windows":
        return "windows"
    if sysname == "linux":
        return "linux"
    return sysname or "unknown"


def data_dir() -> Path:
    if detect_family() == "windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(base) / "DriverScan"
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(base) / "driver-scan"
    path.mkdir(parents=True, exist_ok=True)
    return path


def hostname() -> str:
    return platform.node() or "unknown"


def kernel() -> str:
    return platform.release()


def os_pretty() -> str:
    if platform.system().lower() == "linux":
        path = Path("/etc/os-release")
        if path.exists():
            data: dict[str, str] = {}
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    data[k] = v.strip().strip('"')
            return data.get("PRETTY_NAME") or data.get("NAME") or platform.platform()
    return platform.platform()


def powershell_exe() -> str | None:
    for name in ("pwsh", "powershell", "powershell.exe"):
        found = which(name)
        if found:
            return found
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    bundled = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if bundled.exists():
        return str(bundled)
    return None
