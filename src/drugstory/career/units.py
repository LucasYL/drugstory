"""Player-facing research points.

The rules keep candidate properties on a 0–100 scale. Everything a player reads (evidence ranges,
thresholds, readings, development amounts) is shown ×10, so a small batch of work reads as +21
instead of +2.1. Probabilities, money and character ability keep their own units.
"""

SCALE = 10


def pts(value):
    return int(round(value * SCALE))


def pts_map(values):
    return {key: pts(value) for key, value in values.items()}


def signed(value):
    points = pts(value)
    return f"+{points}" if points >= 0 else str(points)
