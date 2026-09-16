from __future__ import annotations

import argparse
import sys
from pathlib import Path

from driver_scan import __version__
from driver_scan.backup import backup
from driver_scan.fetch import fetch, locate_text
from driver_scan.report import render_html, render_json, render_markdown, render_text
from driver_scan.scan import scan
from driver_scan.schedule import install as schedule_install
from driver_scan.schedule import remove as schedule_remove
from driver_scan.schedule import status as schedule_status

COMMANDS = ("scan", "backup", "schedule", "locate", "fetch")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("-h", "--help", "--version", *COMMANDS):
        argv = ["scan", *argv]
    elif not argv:
        argv = ["scan"]

    parser = argparse.ArgumentParser(
        prog="driver-scan",
        description=(
            "Inventory local hardware: missing, error, firmware, and OS-offered "
            "driver updates. Locate official OEM/OS sources, backup installed "
            "drivers, and schedule repeats."
        ),
    )
    parser.add_argument("--version", action="version", version=f"driver-scan {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan_p = sub.add_parser("scan", help="Scan this machine (default)")
    _add_scan_flags(scan_p)

    bak = sub.add_parser("backup", help="Zip scan report plus driver/config snapshot")
    bak.add_argument("-o", "--output", type=Path, help="Zip path")
    bak.add_argument("--os", choices=("auto", "linux", "windows"), default="auto")

    loc = sub.add_parser("locate", help="Print official PC-maker / chip-vendor URLs for problems")
    loc.add_argument("--os", choices=("auto", "linux", "windows"), default="auto")
    loc.add_argument("--no-windows-update", action="store_true")

    fet = sub.add_parser(
        "fetch",
        help="Write official locate URLs; on Linux apt-get download firmware/driver packages",
    )
    fet.add_argument("-o", "--output", type=Path, default=Path("driver-downloads"))
    fet.add_argument("--os", choices=("auto", "linux", "windows"), default="auto")
    fet.add_argument("--no-windows-update", action="store_true")

    sch = sub.add_parser("schedule", help="Install, show, or remove a repeating scan")
    sch.add_argument("action", choices=("install", "status", "remove"))
    sch.add_argument("--every", choices=("hourly", "daily", "weekly"), default="daily")
    sch.add_argument("--backup", action="store_true", help="Also zip a backup on each run")
    sch.add_argument("--notify", action="store_true", help="Desktop notify when problems > 0 (Linux)")

    args = parser.parse_args(argv)
    if args.cmd == "scan":
        return _cmd_scan(args)
    if args.cmd == "backup":
        return _cmd_backup(args)
    if args.cmd == "locate":
        return _cmd_locate(args)
    if args.cmd == "fetch":
        return _cmd_fetch(args)
    if args.cmd == "schedule":
        return _cmd_schedule(args)
    return 2


def _add_scan_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--os",
        choices=("auto", "linux", "windows"),
        default="auto",
        help="Force collector (default: auto-detect)",
    )
    p.add_argument("--json", action="store_true", help="JSON report on stdout")
    p.add_argument("--markdown", action="store_true", help="Markdown report on stdout")
    p.add_argument("--html", action="store_true", help="Standalone HTML results page")
    p.add_argument("-o", "--output", type=Path, help="Write report to this path")
    p.add_argument("--problems-only", action="store_true", help="Hide ok/skip rows")
    p.add_argument(
        "--no-windows-update",
        action="store_true",
        help="Skip Windows Update COM search (Windows only)",
    )


def _family(args: argparse.Namespace) -> str | None:
    os_choice = getattr(args, "os", "auto")
    return None if os_choice == "auto" else os_choice


def _cmd_scan(args: argparse.Namespace) -> int:
    report = scan(_family(args), include_windows_update=not args.no_windows_update)
    if args.json:
        body = render_json(report, problems_only=args.problems_only)
    elif args.markdown:
        body = render_markdown(report, problems_only=args.problems_only)
    elif args.html:
        body = render_html(report, problems_only=args.problems_only)
    else:
        body = render_text(report, problems_only=args.problems_only)
    if args.output:
        args.output.write_text(body, encoding="utf-8")
        sys.stderr.write(f"wrote {args.output}\n")
    sys.stdout.write(body)
    return 1 if report.problems() else 0


def _cmd_backup(args: argparse.Namespace) -> int:
    path, notes = backup(args.output, family=_family(args))
    sys.stdout.write(f"{path}\n")
    for n in notes:
        sys.stderr.write(f"{n}\n")
    return 0


def _cmd_locate(args: argparse.Namespace) -> int:
    report = scan(_family(args), include_windows_update=not args.no_windows_update)
    sys.stdout.write(locate_text(report))
    return 1 if report.problems() else 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    dest, notes = fetch(
        args.output,
        family=_family(args),
        include_windows_update=not args.no_windows_update,
    )
    sys.stdout.write(f"{dest}\n")
    for n in notes:
        sys.stdout.write(f"{n}\n")
    return 0


def _cmd_schedule(args: argparse.Namespace) -> int:
    if args.action == "install":
        sys.stdout.write(schedule_install(every=args.every, do_backup=args.backup, notify=args.notify) + "\n")
        return 0
    if args.action == "remove":
        sys.stdout.write(schedule_remove() + "\n")
        return 0
    sys.stdout.write(schedule_status() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
