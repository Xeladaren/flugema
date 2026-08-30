
import datetime

def formated_min(min: int) -> str:
    hours = min // 60
    minuts = min - (hours * 60)
    return f"{hours:02}:{minuts:02}"

def datetime_from_db_str(date_str: str | None) -> datetime.datetime:

    if type(date_str) == str:
        date_str = date_str.replace(' ', 'T')
        date_str = f"{date_str}Z"
        return datetime.datetime.fromisoformat(date_str)
    else:
        return None