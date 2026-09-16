# Live Windows capture (process)

A Windows box can dump collector JSON **without** cloning this repo or installing Python. Classified HTML/markdown needs `driver-scan` (clone + venv) on **any** machine that can read the JSON.

Do **not** commit a live JSON file until `serial` is redacted (`driver-scan redact`).

## Why relative `-File` and `cases\` fail

PowerShell `-File` is resolved from the **current directory**, not from the README.

| Command people copy | What happens |
|---------------------|----------------|
| `-File src\driver_scan\windows_collect.ps1` | Fails unless you already `cd` to the clone root. From Desktop/`Downloads` the path does not exist. |
| `-o cases\scan.html` or `.\cases\dell-live.json` | Fails if `cases\` was never created. This repo gitignores `cases/`. |
| Forward-slash `src/driver_scan/...` from `cmd.exe` | Still relative; same cwd problem. |

Use an **absolute** `-File` (`$PSScriptRoot` or a path under `$env:TEMP`) and an **absolute** `-OutFile` (Desktop). `driver-scan -o` now creates parent directories.

## P0 — capture JSON on the Windows box (no clone)

In PowerShell 5.1+ (no admin required):

```powershell
$script = Join-Path $env:TEMP "windows_collect.ps1"
$out = Join-Path $env:USERPROFILE "Desktop\dell-live.json"
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/wbharris/Driver_Scan/main/src/driver_scan/windows_collect.ps1" -OutFile $script
powershell -NoProfile -ExecutionPolicy Bypass -File $script -IncludeWindowsUpdate -OutFile $out
```

If you **did** clone, from the **repo root**:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "$PWD\src\driver_scan\windows_collect.ps1" -IncludeWindowsUpdate -OutFile "$env:USERPROFILE\Desktop\dell-live.json"
```

Confirm `wrote C:\Users\...\Desktop\dell-live.json`. Copy that file off the box.

## P0 — classify HTML/markdown (machine with Python)

```bash
cd Driver_Scan
.venv/bin/driver-scan redact path/to/dell-live.json -o tests/data/windows11-latitude-5490.json
.venv/bin/driver-scan --fixture tests/data/windows11-latitude-5490.json --include-ignored --problems-only
.venv/bin/driver-scan --fixture tests/data/windows11-latitude-5490.json --include-ignored --html -o cases/latitude-5490.html
```

`redact` blanks `serial` / `serialNumber` / `product_serial`. Do not commit unredacted JSON.

## P1 — after capture

- [ ] Collector JSON exists and is non-empty
- [ ] `serial` is `REDACTED` (or the file is not in git)
- [ ] `driver-scan --fixture` ran (problems-only text)
- [ ] HTML written (`--html -o …`; parent dirs are created)
- [ ] Markdown optional (`--markdown -o …`)
- [ ] Live JSON is **not** committed until redacted

## Latitude 5490 (this capture)

Collector JSON on the Dell **succeeded**. Classified HTML/markdown **did not run** on that box (no clone, no `driver-scan`). Next operator step is the P0 classify commands above on a machine that has this repo, using the copied JSON after `redact`.
