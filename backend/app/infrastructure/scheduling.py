import re


def daily_slots(*times: str) -> tuple[tuple[int, int], ...]:
    if not times:
        raise ValueError("At least one daily time is required")
    slots = set()
    for value in times:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{2}:[0-9]{2}", value):
            raise ValueError("Daily times must use HH:MM")
        hour, minute = map(int, value.split(":"))
        if hour > 23 or minute > 59:
            raise ValueError("Daily time is out of range")
        if (hour, minute) in slots:
            raise ValueError("Duplicate daily time")
        slots.add((hour, minute))
    return tuple(sorted(slots))
