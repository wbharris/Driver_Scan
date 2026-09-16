from __future__ import annotations

import argparse
import sys
from pathlib import Path

from driver_scan import __version__
from driver_scan.report import render_json, render_markdown, render_text
from driver_scan.scan import scan


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in ("-h", "--help", "--version", "scan"):
        argv = ["scan", *argv]
    elif not argv:
        argv = ["scan"]

    parser = argparse.ArgumentParser(
        prog="driver-scan",
        description=(
            "Inventory local hardware and report missing, error, firmware, "
            "and OS-offered driver updates. Official vendor/OS sources only."
        ),
    )
    parser.add_argument("--version", action="version", version=f"driver-scan {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    scan_p = sub.add_parser("scan", help="Scan this machine (default)")
    _add_scan_flags(scan_p)

    args = parser.parse_args(argv)
    return _cmd_scan(args)


def _add_scan_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--os",
        choices=("auto", "linux", "windows"),
        default="auto",
        help="Force collector (default: auto-detect)",
    )
    p.add_argument("--json", action="store_true", help="JSON report on stdout")
    p.add_argument("--markdown", action="store_true", help="Markdown report on stdout")
    p.add_argument("-o", "--output", type=Path, help="Write report to this path")
    p.add_argument(
        "--problems-only",
        action="store_true",
        help="Hide ok/skip rows",
    )
    p.add_argument(
        "--no-windows-update",
        action="store_true",
        help="Skip Windows Update COM search (Windows only)",
    )


def _cmd_scan(args: argparse.Namespace) -> int:
    family = None if args.os == "auto" else args.os
    report = scan(family, include_windows_update=not args.no_windows_update)
    if args.json:
        body = render_json(report, problems_only=args.problems_only)
    elif args.markdown:
        body = render_markdown(report, problems_only=args.problems_only)
    else:
        body = render_text(report, problems_only=args.problems_only)
    if args.output:
        args.output.write_text(body, encoding="utf-8")
        sys.stderr.write(f"wrote {args.output}\n")
    sys.stdout.write(body)
    return 1 if report.problems() else 0


if __name__ == "__main__":
    raise SystemExit(main())
