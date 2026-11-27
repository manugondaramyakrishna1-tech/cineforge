"""Small, testable helpers for editable movie timelines."""

def move_item(items, index, direction):
    """Move an item one slot up (-1) or down (+1), returning a new list."""
    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1")
    if index < 0 or index >= len(items):
        raise IndexError("index out of range")
    target = index + direction
    if target < 0 or target >= len(items):
        return list(items)
    result = list(items)
    result[index], result[target] = result[target], result[index]
    return result


def validate_timeline(items):
    """Validate scene entries and return total duration."""
    total = 0
    for item in items:
        if not isinstance(item, dict):
            raise TypeError("Each timeline entry must be a dictionary")
        seconds = item.get("seconds")
        if not isinstance(seconds, (int, float)) or seconds <= 0:
            raise ValueError("Scene durations must be positive numbers")
        total += seconds
    return total
