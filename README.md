# Driver Scan™

A **GitHub agent** plus a small CLI that **inventories this machine** and reports **missing, error, firmware, and OS-offered driver updates** on **Linux and Windows**.

Not a DriverAgent® clone. Not a third-party driver pack. It does **not** download or install vendor `.exe` / `.inf` blobs from the internet. Official sources only: Windows Update, the distro package manager, and the PC/chip maker’s support page.

Repo: https://github.com/wbharris/Driver_Scan

Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md). Copilot / coding-agent profile: [`.github/agents/driver-scan.md`](.github/agents/driver-scan.md).

**Driver Scan™** is a trademark of wbharris (common-law ™). See [`TRADEMARK.md`](TRADEMARK.md).

DriverAgent® is a trademark of its owner. This project is not affiliated with eSupport.com. Historical listing we used as the job description: [DriverAgent 3.2016.7.7 on MajorGeeks](https://www.majorgeeks.com/files/details/driveragent.html). See [`CREDITS.md`](CREDITS.md).

## What it finds

| Severity | Meaning |
|----------|---------|
| `missing` | Hardware present, no driver bound (Linux) or Device Manager code 28 (Windows) |
| `error` | Device started and failed (code 10/31/43/52, DKMS broken) |
| `firmware` | Kernel log shows a firmware load failure |
| `update` | Distro packages (`linux-firmware`, NVIDIA, mesa, …) or Windows Update **driver** offers |
| `ok` / `skip` | Bound and healthy, or chipset/hub functions that never have a loadable driver |

## Install

```bash
git clone https://github.com/wbharris/Driver_Scan.git
cd Driver_Scan
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

Windows (PowerShell):

```powershell
git clone https://github.com/wbharris/Driver_Scan.git
cd Driver_Scan
py -3 -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
```

Python 3.11+. No extra runtime packages. Windows collection uses the bundled `windows_collect.ps1` (PowerShell 5.1 or pwsh).

## Usage

```bash
driver-scan
driver-scan --problems-only
driver-scan --json
driver-scan --markdown -o cases/$(hostname).md
```

```text
driver-scan --os linux
driver-scan --os windows --no-windows-update
```

Exit code **1** if any `missing` / `error` / `firmware` / `update` finding exists, else **0**.

On Windows without Python you can still dump JSON:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File src\driver_scan\windows_collect.ps1 -IncludeWindowsUpdate
```

## Agent

On GitHub.com Copilot coding agent / VS Code custom agents: select **Driver Scan** (`.github/agents/driver-scan.md`). It runs `driver-scan --markdown --problems-only` and stops at official next steps.

## Honesty

- “Outdated” means the **OS** offered an update (apt / Windows Update), not a scraped commercial driver catalog.
- Chipset bridges, ISA/PMC, and USB hubs are `skip`, not missing.
- Firmware lines need `dmesg` or `journalctl` permission; if those fail, the report lists them under skipped tools.
- Do not install random driver-updater apps. Prefer Windows Update, then Dell/HP/Lenovo/ASUS, then Intel/AMD/NVIDIA.

## License

GPL-3.0-or-later. See [`LICENSE`](LICENSE).
