"""Date handling. Partitions are calendar days in Spanish peninsular local time."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MARKET_TZ = ZoneInfo("Europe/Madrid")


def parse_day(value: str) -> date:
    """Parse a strict ``YYYY-MM-DD`` string."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"Expected a date as YYYY-MM-DD, got {value!r}") from exc


def resolve_target_day(explicit: str | None, reference: datetime) -> date:
    """Pick the day a pipeline run should process.

    An explicit ``YYYY-MM-DD`` wins (manual runs and backfills). Otherwise the
    target is the last complete local day before ``reference``, which must be
    timezone-aware (schedulers hand out UTC timestamps).
    """
    if explicit:
        return parse_day(explicit)
    if reference.tzinfo is None:
        raise ValueError("reference must be timezone-aware")
    return reference.astimezone(MARKET_TZ).date() - timedelta(days=1)
