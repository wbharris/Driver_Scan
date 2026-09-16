from __future__ import annotations

import argparse
import sys
from pathlib import Path

from driver_scan import __version__
from driver_scan.backup import backup, restore
from driver_scan.fetch import fetch, locate_text
from driver_scan.guide import guide_text
from driver_scan.ignore import add_ignore, load_ignored, remove_ignore
from driver_scan.report import render_html, render_json, render_list, render_markdown, render_text
from driver_scan.scan import scan
from driver_scan.schedule import install as schedule_install
from driver_scan.schedule import remove as schedule_remove
from driver_scan.schedule import status as schedule_status
from driver_scan.util import notify as desktop_notify

COMMANDS = ("scan", "backup", "schedule", "locate", "fetch", "restore", "guide", "list", "ignore")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("-h", "--help", "--version", *COMMANDS):
        argv = ["scan", *argv]
    elif not argv:
        argv = ["scan"]

    parser = argparse.ArgumentParser(
        prog="driver-scan",
        description=(
            "Inventory local hardware: missing, mismatched, error, firmware, and "
            "OS-offered driver updates. Locate official OEM/OS sources, backup "
            "and restore, guide next steps, and schedule repeats."
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
    _add_view_flags(loc)

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

    rst = sub.add_parser("restore", help="Restore a backup zip (dry-run unless --apply)")
    rst.add_argument("archive", type=Path)
    rst.add_argument("--apply", action="store_true", help="Write configs / pnputil /add-driver")
    rst.add_argument("--only", help="Restore only archive members whose names contain this string")
    rst.add_argument("--os", choices=("auto", "linux", "windows"), default="auto")

    g = sub.add_parser("guide", help="Ordered next steps from a fresh scan")
    _add_view_flags(g)

    lst = sub.add_parser("list", help="All installed drivers in one place, by class")
    _add_view_flags(lst)

    ign = sub.add_parser("ignore", help="Hide a device from problem counts")
    ign.add_argument("action", choices=("list", "add", "remove"))
    ign.add_argument("id", nargs="?", help="Finding id, name, or vendor:device")

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
    if args.cmd == "restore":
        return _cmd_restore(args)
    if args.cmd == "guide":
        return _cmd_guide(args)
    if args.cmd == "list":
        return _cmd_list(args)
    if args.cmd == "ignore":
        return _cmd_ignore(args)
    return 2


def _add_scan_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="JSON report on stdout")
    p.add_argument("--markdown", action="store_true", help="Markdown report on stdout")
    p.add_argument("--html", action="store_true", help="Standalone HTML results page")
    p.add_argument("-o", "--output", type=Path, help="Write report to this path")
    p.add_argument("--problems-only", action="store_true", help="Hide ok/skip rows")
    p.add_argument("--notify", action="store_true", help="Desktop notify when problems > 0")
    _add_view_flags(p)


def _nonneg_int(value: str) -> int:
    try:
        n = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if n < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return n


def _add_view_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--os",
        choices=("auto", "linux", "windows"),
        default="auto",
        help="Force collector (default: auto-detect)",
    )
    p.add_argument("--category", action="append", dest="categories", help="Repeatable: graphics, audio, network, printer, imaging, …")
    p.add_argument(
        "--older-than",
        type=_nonneg_int,
        metavar="DAYS",
        help="Keep rows whose driver date is at least this many days old (0 = dated today or earlier)",
    )
    p.add_argument("--include-ignored", action="store_true", help="Do not apply the ignore list")
    p.add_argument(
        "--fixture",
        type=Path,
        help="Replay a collector JSON (Windows PnP payload or Linux lspci/lsusb text)",
    )
    p.add_argument(
        "--no-windows-update",
        action="store_true",
        help="Skip Windows Update COM search (Windows only)",
    )


def _family(args: argparse.Namespace) -> str | None:
    os_choice = getattr(args, "os", "auto")
    return None if os_choice == "auto" else os_choice


def _scan_kwargs(args: argparse.Namespace) -> dict:
    return {
        "family": _family(args),
        "include_windows_update": not getattr(args, "no_windows_update", False),
        "include_ignored": getattr(args, "include_ignored", False),
        "categories": getattr(args, "categories", None),
        "older_than_days": getattr(args, "older_than", None),
        "fixture": getattr(args, "fixture", None),
    }


def _cmd_scan(args: argparse.Namespace) -> int:
    report = scan(**_scan_kwargs(args))
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
    if args.notify and report.problems():
        desktop_notify("Driver Scan", f"{len(report.problems())} problem(s) on {report.hostname}")
    return 1 if report.problems() else 0


def _cmd_backup(args: argparse.Namespace) -> int:
    path, notes = backup(args.output, family=_family(args))
    sys.stdout.write(f"{path}\n")
    for n in notes:
        sys.stderr.write(f"{n}\n")
    return 0


def _cmd_locate(args: argparse.Namespace) -> int:
    report = scan(**_scan_kwargs(args))
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


def _cmd_restore(args: argparse.Namespace) -> int:
    notes = restore(args.archive, apply=args.apply, family=_family(args), only=args.only)
    for n in notes:
        sys.stdout.write(f"{n}\n")
    return 0


def _cmd_guide(args: argparse.Namespace) -> int:
    report = scan(**_scan_kwargs(args))
    sys.stdout.write(guide_text(report))
    return 1 if report.problems() else 0


def _cmd_list(args: argparse.Namespace) -> int:
    report = scan(**_scan_kwargs(args))
    sys.stdout.write(render_list(report))
    return 1 if report.problems() else 0


def _cmd_ignore(args: argparse.Namespace) -> int:
    if args.action == "list":
        ids = load_ignored()
        sys.stdout.write("\n".join(ids) + ("\n" if ids else "(empty)\n"))
        return 0
    if not args.id:
        sys.stderr.write("ignore add/remove needs an id\n")
        return 2
    ids = add_ignore(args.id) if args.action == "add" else remove_ignore(args.id)
    sys.stdout.write("\n".join(ids) + ("\n" if ids else "(empty)\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
