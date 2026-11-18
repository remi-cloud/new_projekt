"""Keep SQLite LIMIT in 1..max. A negative limit means no limit in SQLite."""


def bounded_limit(limit: int, maximum: int) -> int:
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 1
    if value < 1:
        value = 1
    if value > maximum:
        value = maximum
    return value
