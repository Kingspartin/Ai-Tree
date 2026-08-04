"""igwatch - watch an Instagram username and get alerted when it frees up."""

__version__ = "1.0.0"

from .models import Availability, CheckResult

__all__ = ["Availability", "CheckResult", "__version__"]
