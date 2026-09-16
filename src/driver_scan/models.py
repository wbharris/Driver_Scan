from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Severity = Literal["missing", "error", "firmware", "update", "ok", "skip"]
Bus = Literal["pci", "usb", "pnp", "package", "firmware", "dkms", "system"]

PROBLEM_SEVERITIES = frozenset({"missing", "error", "firmware", "update"})


@dataclass
class Finding:
    id: str
    severity: Severity
    bus: Bus
    name: str
    detail: str
    vendor_id: str | None = None
    device_id: str | None = None
    driver: str | None = None
    version: str | None = None
    modules: list[str] = field(default_factory=list)
    official_url: str | None = None
    suggested: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    hostname: str
    os: str
    kernel: str
    scanned_at: str
    oem: str | None = None
    model: str | None = None
    serial: str | None = None
    oem_url: str | None = None
    findings: list[Finding] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    tools_skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def problems(self) -> list[Finding]:
        return [f for f in self.findings if f.severity in PROBLEM_SEVERITIES]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.severity] = out.get(f.severity, 0) + 1
        return out

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["counts"] = self.counts()
        d["problem_count"] = len(self.problems())
        return d


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
