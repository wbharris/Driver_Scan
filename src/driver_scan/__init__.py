"""Driver Scan™ — local hardware driver inventory."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("driver-scan")
except PackageNotFoundError:
    __version__ = "0.3.0"

__all__ = ["__version__"]
