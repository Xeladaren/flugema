
import datetime

def formated_min(min: int) -> str:
    """Format a duration expressed in minutes as an ``HH:MM`` string.

    The number of minutes is split into whole hours and remaining minutes,
    both zero-padded to two digits. The hours part is not capped at 24, so
    durations longer than a day are rendered as-is (e.g. ``1500`` -> ``"25:00"``).

    Args:
        min: The duration in minutes. Expected to be a non-negative integer.

    Returns:
        The duration formatted as ``"HH:MM"``.
    """
    hours = min // 60
    minuts = min - (hours * 60)
    return f"{hours:02}:{minuts:02}"

def datetime_from_db_str(date_str: str | None) -> datetime.datetime | None:
    """Convert a database date string into a timezone-aware ``datetime`` object.

    Database timestamps are stored as ISO-like strings using a space as the
    separator between the date and the time parts (e.g. ``"2024-05-17 08:30:00"``)
    and are assumed to be expressed in UTC. This helper normalizes the string
    (replacing the space separator with ``"T"`` and appending the ``"Z"`` UTC
    designator) before parsing it.

    Args:
        date_str: The date string coming from the database, or ``None``.

    Returns:
        A timezone-aware ``datetime.datetime`` in UTC, or ``None`` if
        ``date_str`` is not a string (e.g. ``None``).

    Raises:
        ValueError: If ``date_str`` is a string that is not a valid ISO 8601
            timestamp.
    """
    if type(date_str) == str:
        date_str = date_str.replace(' ', 'T')
        date_str = f"{date_str}Z"
        return datetime.datetime.fromisoformat(date_str)
    else:
        return None

def print_hour(date: datetime.datetime | str | None):
    if type(date) == str:
        date = datetime.datetime.fromisoformat(date)
    if date:
        return date.time().isoformat(timespec='minutes')
    else:
        return "--:--"