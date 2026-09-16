from __future__ import annotations

from datetime import datetime, timedelta, timezone

from driver_scan.models import Finding, Report


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()[:10]
    try:
        return datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def is_older_than(finding: Finding, days: int) -> bool:
    dt = parse_date(finding.driver_date)
    if dt is None:
        return False
    return dt <= datetime.now(timezone.utc) - timedelta(days=days)


def apply_view_filters(
    report: Report,
    *,
    categories: list[str] | None = None,
    older_than_days: int | None = None,
) -> None:
    if not categories and not older_than_days:
        return
    wanted = {c.lower() for c in (categories or [])}
    kept: list[Finding] = []
    for f in report.findings:
        if wanted and f.category.lower() not in wanted:
            continue
        if older_than_days and not is_older_than(f, older_than_days):
            continue
        kept.append(f)
    report.findings = kept
    bits = []
    if wanted:
        bits.append("categories " + ",".join(sorted(wanted)))
    if older_than_days:
        bits.append(f"driver date older than {older_than_days}d")
    report.notes.append("view filter: " + "; ".join(bits))
