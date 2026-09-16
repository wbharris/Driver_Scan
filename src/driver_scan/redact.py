from __future__ import annotations

from typing import Any

SERIAL_KEYS = frozenset({"serial", "product_serial", "serialnumber", "biosserial"})


def redact_obj(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if str(key).lower() in SERIAL_KEYS and isinstance(item, str) and item.strip():
                out[key] = "REDACTED"
            else:
                out[key] = redact_obj(item)
        return out
    if isinstance(value, list):
        return [redact_obj(item) for item in value]
    return value
