# Driver Scan™ product contract

End goal: an agent (and CLI) **scans the local machine** for hardware that has **no driver**, a **mismatched/fallback driver**, a **failed driver**, **missing firmware**, or an **OS-offered driver/firmware update**, on **Linux and Windows**, then can **guide** official next steps, **locate** sources, **fetch** OS packages, **backup/restore**, and **schedule** repeats.

Repo: https://github.com/wbharris/Driver_Scan

**Driver Scan™** is a trademark of wbharris (common-law ™). See [`TRADEMARK.md`](../TRADEMARK.md).

## Why this exists

1. What hardware is here?
2. What has no driver, is broken, or has an OS-offered update?
3. Where is the **official** fix?
4. Can I snapshot what is installed, and run this again on a timer?

Driver Scan does (1)–(4). It does not host installers, scrape a private driver database, or auto-install third-party packs.

## User journey

```
this machine
     │
     ▼
1. Detect OS family (linux | windows) + chassis OEM (DMI / WMI)
     │
     ▼
2. Inventory
   Linux:  lspci -nnk, lsusb + sysfs bind, dmesg/journal firmware,
           dkms, ubuntu-drivers, apt/dnf upgradable (firmware/GPU), modinfo version
   Windows: Win32_PnPEntity, Win32_PnPSignedDriver (version + date),
            optional Microsoft.Update.Session Type='Driver'
     │
     ▼
3. Classify  missing | mismatch | error | firmware | update | ok | skip
   Categories: graphics, audio, network, chipset, storage, printer, imaging, usb, other
     │
     ▼
4. Report  text | markdown | json | html
   official_url = chip vendor; oem_url = PC maker
     │
     ├─ locate  unique official URLs
     ├─ fetch   LINKS.txt + apt-get/dnf download (Linux OS packages only)
     ├─ backup  zip (report + pnputil export or Linux config snapshot)
     └─ schedule  systemd --user timer or schtasks
```

## Commands

| Command | Behavior |
|---------|----------|
| `scan` | Inventory + classify. Default if no subcommand. `--notify` for a desktop alert. `--category`, `--older-than DAYS`. `--fixture FILE` replays Windows PnP JSON or Linux lspci/lsusb text |
| `list` | All installed drivers grouped by class (see everything in one place) |
| `guide` | Numbered playbook: backup, OS update, PC maker, vendor, restore |
| `locate` | Print PC-maker URL and per-problem chip-vendor URLs |
| `fetch` | `LINKS.txt`; Linux also `apt-get download` or `dnf download` matching firmware/driver packages |
| `backup` | Zip report + driver store export (Windows) or lspci/lsusb/modprobe.d/dkms (Linux) |
| `restore` | Dry-run a backup zip; `--apply` restores Linux configs or Windows INF via pnputil (Windows restore point first). `--only` |
| `ignore` | Persist device ids that should not count as problems |
| `redact` | Blank serial fields in collector JSON before share/commit |
| `schedule install\|status\|remove` | Hourly/daily/weekly scan; optional `--backup` `--notify` |

## Collectors

| OS | Required tools | Optional |
|----|----------------|----------|
| Linux | `lspci`, `lsusb`, `/sys` | `dmesg` / `journalctl`, `dkms`, `ubuntu-drivers`, `apt`, `dnf`, `modinfo`, DMI |
| Windows | PowerShell + CIM | Windows Update COM search (`--no-windows-update` skips), `pnputil`, `schtasks` |

Missing tools are **skipped and named**, not a crash.

## Classification rules

**Linux PCI**

- `Kernel driver in use` → `ok` (modinfo version when present)
- NVIDIA bound to `nouveau`, or graphics on `vesa`/`simpledrm` → `mismatch`
- `Kernel modules` listed, no driver in use → `missing`
- Neither, and class is not a bridge/PMC → `missing`
- PCI class `0600` / `0601` / `0604` / `0580` without a driver → `skip`

**Linux USB**

- Root hubs and generic hubs → `skip`
- sysfs `driver` symlink → `ok`
- Else → `missing`

**Windows ConfigManagerErrorCode**

- `28` → `missing`
- Generic Basic Display / Standard VGA, or codes `32` / `39` / `48` → `mismatch`
- `10`, `31`, `43`, `52`, and other failure codes → `error`
- `22` (disabled), `45` (not connected) → `skip`
- `0` → `ok` (plus a separate `update` row if Windows Update offers a driver)

**Updates**

- Linux: `apt list --upgradable` or `dnf check-update` rows matching firmware / microcode / nvidia / mesa / iwlwifi / similar
- Windows: `IsInstalled=0 and Type='Driver'`
- No commercial “latest version” comparison

## Non-goals

- Installing drivers without the operator
- Fetching `.inf` / `.sys` / `.exe` from arbitrary websites
- A paid catalog of “outdated” versions
- macOS / BSD (later)

## Outputs

CLI: `driver-scan` (also `python -m driver_scan`). Exit `1` when problem findings exist (scan/locate).

GitHub agent profile: `.github/agents/driver-scan.md`.
