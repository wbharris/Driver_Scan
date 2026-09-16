# Driver Scan™

A **GitHub agent** plus a small CLI that **inventories this machine** and reports **missing, error, firmware, and OS-offered driver updates** on **Linux and Windows**.

It does **not** download or install vendor `.exe` / `.inf` blobs from the internet. Official sources only: Windows Update, the distro package manager, and the PC/chip maker’s support page.

Repo: https://github.com/wbharris/Driver_Scan

Contract: [`docs/PRODUCT.md`](docs/PRODUCT.md). Copilot / coding-agent profile: [`.github/agents/driver-scan.md`](.github/agents/driver-scan.md).

**Driver Scan™** is a trademark of wbharris (common-law ™). See [`TRADEMARK.md`](TRADEMARK.md).

## What it does

| Command | Job |
|---------|-----|
| `driver-scan` / `scan` | Fast inventory: missing, error, firmware, OS-offered updates |
| `driver-scan --html` | Stand-alone results page |
| `locate` | Official PC-maker and chip-vendor URLs for problem devices |
| `fetch -o DIR` | Write `LINKS.txt`; on Linux `apt-get download` firmware/driver packages into DIR (progress per package) |
| `backup -o FILE.zip` | Zip the report plus a driver/config snapshot (Windows: `pnputil /export-driver`; Linux: lspci/lsusb, modprobe.d, dkms) |
| `schedule install` | Repeat the scan (systemd user timer or Windows Task Scheduler): hourly / daily / weekly, optional backup + notify |

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
driver-scan --html -o cases/$(hostname).html
driver-scan --markdown -o cases/$(hostname).md
driver-scan locate
driver-scan fetch -o ./driver-downloads
driver-scan backup -o ./drivers.zip
driver-scan schedule install --every daily --backup --notify
driver-scan schedule status
driver-scan schedule remove
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

- “Outdated” means the **OS** offered an update (apt / Windows Update), not a scraped commercial catalog.
- Chipset bridges, ISA/PMC, and USB hubs are `skip`, not missing.
- Firmware lines need `dmesg` or `journalctl` permission; if those fail, the report lists them under skipped tools.
- Prefer Windows Update, then Dell/HP/Lenovo/ASUS, then Intel/AMD/NVIDIA.
- `fetch` never pulls random `.exe` / `.inf` from the web. Linux downloads distro packages only.

## License

GPL-3.0-or-later. See [`LICENSE`](LICENSE).
