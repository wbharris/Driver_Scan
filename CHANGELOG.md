# Changelog

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
