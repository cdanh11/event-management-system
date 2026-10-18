"""Small statistics helpers shared by the opt-in benchmark commands."""
import math
import statistics


def summarize_ms(values: list[float]) -> dict[str, float | int]:
    """Nearest-rank p95; include sample count so small runs are recognizable."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("At least one timing sample is required")
    return {
        "samples": len(ordered),
        "mean_ms": round(statistics.mean(ordered), 3),
        "median_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[math.ceil(0.95 * len(ordered)) - 1], 3),
        "min_ms": round(ordered[0], 3),
        "max_ms": round(ordered[-1], 3),
    }
