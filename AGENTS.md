# Agent notes (Driver Scan)

This repository is the **Driver Scan** product: a CLI plus a GitHub custom agent that inventories local hardware and reports missing/broken/firmware/OS-offered drivers.

Read `docs/PRODUCT.md` before changing classification rules.

- CLI entry: `driver-scan` → `driver_scan.cli:main` (`scan`, `list`, `guide`, `locate`, `fetch`, `backup`, `restore`, `ignore`, `schedule`)
- Linux parse/collect: `src/driver_scan/linux.py`
- Windows parse: `src/driver_scan/windows.py` + `windows_collect.ps1`
- Official URLs: `src/driver_scan/vendors.py` only
- Copilot agent profile: `.github/agents/driver-scan.md`

Do not add installer downloaders, driver-pack mirrors, or auto-install of vendor binaries. `fetch` may only `apt-get download` distro packages and write official OEM/OS links.
