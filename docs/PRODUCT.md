# Driver Scan™ product contract

End goal: an agent (and CLI) **scans the local machine** for hardware that has **no driver**, a **failed driver**, **missing firmware**, or an **OS-offered driver/firmware update**, on **Linux and Windows**, and writes one report.

Repo: https://github.com/wbharris/Driver_Scan

**Driver Scan™** is a trademark of wbharris (common-law ™). See [`TRADEMARK.md`](../TRADEMARK.md).

Not affiliated with DriverAgent® / eSupport.com.

## Why this exists

Classic “driver updater” apps (including the old Driver Agent class) scan hardware then push a **paid pack of binaries**. Those products are often bundled PUAs. The job people actually wanted was:

1. What hardware is here?
2. What has no driver or a broken one?
3. Where is the **official** fix?

Driver Scan does (1)–(3). It does not host installers, scrape a private driver database, or auto-install third-party packs.

## User journey

```
this machine
     │
     ▼
1. Detect OS family (linux | windows)
     │
     ▼
2. Inventory
   Linux:  lspci -nnk, lsusb + sysfs bind, dmesg/journal firmware,
           dkms, ubuntu-drivers, apt upgradable (firmware/GPU)
   Windows: Win32_PnPEntity, Win32_PnPSignedDriver,
            optional Microsoft.Update.Session Type='Driver'
     │
     ▼
3. Classify  missing | error | firmware | update | ok | skip
     │
     ▼
4. Report  text | markdown | json
   official_url = OEM or chip vendor support page
     │
     ▼
5. Stop
   Operator installs from Windows Update / apt / OEM. Agent does not.
```

## Collectors

| OS | Required tools | Optional |
|----|----------------|----------|
| Linux | `lspci`, `lsusb`, `/sys` | `dmesg` / `journalctl`, `dkms`, `ubuntu-drivers`, `apt` |
| Windows | PowerShell + CIM | Windows Update COM search (`--no-windows-update` skips) |

Missing tools are **skipped and named**, not a crash.

## Classification rules

**Linux PCI**

- `Kernel driver in use` → `ok`
- `Kernel modules` listed, no driver in use → `missing`
- Neither, and class is not a bridge/PMC → `missing`
- PCI class `0600` / `0601` / `0604` / `0580` without a driver → `skip`

**Linux USB**

- Root hubs and generic hubs → `skip`
- sysfs `driver` symlink → `ok`
- Else → `missing`

**Windows ConfigManagerErrorCode**

- `28` → `missing`
- `10`, `31`, `43`, `52`, and other failure codes → `error`
- `22` (disabled), `45` (not connected) → `skip`
- `0` → `ok` (plus a separate `update` row if Windows Update offers a driver)

**Updates**

- Linux: `apt list --upgradable` rows matching firmware / microcode / nvidia / mesa / iwlwifi / similar
- Windows: `IsInstalled=0 and Type='Driver'`
- No commercial “latest version” comparison

## Non-goals

- Installing drivers
- Hosting or fetching `.inf` / `.sys` / `.exe` from the internet
- A paid catalog of “outdated” versions
- macOS / BSD (later)

## Outputs

CLI: `driver-scan` (also `driver-scan scan`). Exit `1` when problem findings exist.

GitHub agent profile: `.github/agents/driver-scan.md`.
