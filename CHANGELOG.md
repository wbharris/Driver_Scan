# Changelog

## 0.4.8

- Windows live capture: collector `-OutFile`, README no-clone absolute `-File`, `docs/LIVE-WINDOWS.md`.
- `driver-scan -o` creates parent dirs (`cases\`).
- `driver-scan redact` blanks serials. `*live.json` is gitignored.

## 0.4.7

- Scheduled Linux runner captures scan status 1 so backup/notify still run; Windows runner preserves the same status.
- Failed Win32_PnPEntity collection is an incomplete/error scan, not a clean exit 0.
- ZIP restore copies in chunks with per-member and total size caps.

## 0.4.6

- Windows collector records CIM/WU errors instead of swallowing them; skips unplugged devices; Python keeps JSON if PowerShell exits non-zero.
- `fetch` uses `dnf download` when apt is absent; live Linux scan uses `dnf check-update`.
- Schedule notify matches problem counts of 10+.
- PRODUCT.md categories and fetch/dnf docs match the code.

## 0.4.5

- Restore extracts only validated zip members (no `extractall`, reject `..` paths).
- `--older-than 0` is a real filter; negative values are rejected.
- Ignore list matches finding id, name, or vendor:device exactly (case-insensitive).

## 0.4.4

- dnf/yum upgradable parse for RHEL-style package lists.
- RHEL 10.2 simulation (`tests/simulate_rhel102.py`, kernel 6.12.0-211.7.1.el10_2).

## 0.4.3

- Linux collector fixtures (`family: linux` + lspci/lsusb/dmesg/apt text).
- Ubuntu 26.04.1 LTS simulation (`tests/simulate_ubuntu2604.py`). 26.10 is not GA yet.

## 0.4.2

- Windows Server 2025 Datacenter simulation (`tests/data/windowsserver2025-poweredge.json`, build 26100.33451).

## 0.4.1

- `--fixture FILE` replays a Windows collector JSON (Windows 11 simulation on Linux).
- `tests/simulate_windows11.py` and `tests/data/windows11-dell.json` (Dell XPS 15 9530, 24H2).

## 0.4.0

- `list` — every installed driver in one place, grouped by class (graphics, audio, network, storage, printer, imaging, …).
- `--category` and `--older-than DAYS` view filters (age is inventory, not a fake “outdated” catalog).
- `ignore add|remove|list` so a device can be hidden from problem counts.
- `restore --only` for a subset; Windows `--apply` tries a System Restore point first.

## 0.3.0

- `mismatch` for generic/fallback or OS-incompatible drivers (graphics/audio/network/chipset classes on the report).
- `guide` ordered next steps; `restore` from a backup zip (`--apply` to write).
- `scan --notify` when problems exist.

## 0.2.0

- Chassis OEM from DMI / WMI (PC-maker support URL on the report).
- HTML results page (`--html`).
- `locate` official URLs; `fetch` writes `LINKS.txt` and on Linux `apt-get download`s firmware/driver packages.
- `backup` zip (Windows `pnputil /export-driver`, Linux report + modprobe.d / dkms / lspci).
- `schedule install|status|remove` (systemd --user or Task Scheduler), optional backup and notify.
- Bound-driver versions via `modinfo` / signed-driver version.

## 0.1.0

- First cut: Linux (`lspci` / `lsusb` / firmware log / apt / dkms) and Windows (PnP + optional Windows Update driver search).
- CLI `driver-scan`, JSON/markdown/text reports, GitHub custom agent at `.github/agents/driver-scan.md`.
- Official OEM/chip-vendor URLs only.
