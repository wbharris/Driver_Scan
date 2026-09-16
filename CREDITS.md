# Credits

## Historical reference

The scan-and-report job is the same one **DriverAgent** (eSupport.com, Inc.) advertised to Windows users:

- MajorGeeks listing (cached product page): https://www.majorgeeks.com/files/details/driveragent.html
- Version on that page: **3.2016.7.7** (dated 06/21/18, ~1.16 MB, shareware $29.95)
- Windows XP through 10
- Stated features: fast scan for **out-of-date and missing** drivers, a private database (“17 million driver files”), download manager, zip backup, scheduled scans

Driver Scan is **original code**. It is **not** a fork, rebrand, or compatible client of DriverAgent. It does **not** use eSupport’s catalog, installer, or download manager.

What we kept as the *job*: identify missing / broken drivers on this machine.

What we dropped on purpose:

| DriverAgent (MajorGeeks listing) | Driver Scan |
|----------------------------------|-------------|
| Windows only | Linux and Windows |
| Paid database of driver binaries | No hosted/pack downloads |
| Download + install from that database | Official OS / OEM / chip-vendor links only |
| Driver backup zip, schedule manager | Not in v0.1 (report only) |

**DriverAgent** is a mark of its owner. This project is not affiliated with, endorsed by, or connected to eSupport.com.

## Tools used when present

Linux: pciutils (`lspci`), usbutils (`lsusb`), sysfs, dmesg/journalctl, dkms, apt, ubuntu-drivers.

Windows: Win32_PnPEntity, Win32_PnPSignedDriver, Microsoft Update Agent (`Type='Driver'`).
