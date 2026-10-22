"""Strength standards and 1RM estimation.

Tables are ratios of estimated 1RM to bodyweight, for an adult lifter, by sex.
The five columns map to the usual tiers:

    beginner, novice, intermediate, advanced, elite

and we treat those as roughly the 5th / 20th / 50th / 80th / 95th percentile
of the gym-going population. These are approximations pulled together from
publicly available strength standard tables, rounded; they are not a licensed
dataset and shouldn't be read as precise. Good enough for a "where am I"
rating, which is all this is meant to be.

For bodyweight moves (pull-up, dip) the ratio is (bodyweight + added) / bodyweight,
so an unweighted rep is 1.0.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

TIERS = ("beginner", "novice", "intermediate", "advanced", "elite")
TIER_PERCENTILE = (5, 20, 50, 80, 95)

# ratio 1RM / bodyweight
STANDARDS: dict[str, dict[str, tuple[float, ...]]] = {
    "bench":     {"male": (0.50, 0.75, 1.00, 1.50, 2.00), "female": (0.25, 0.50, 0.75, 1.00, 1.25)},
    "squat":     {"male": (0.75, 1.25, 1.50, 2.25, 2.75), "female": (0.50, 0.75, 1.25, 1.50, 2.00)},
    "deadlift":  {"male": (1.00, 1.50, 2.00, 2.50, 3.00), "female": (0.50, 1.00, 1.25, 1.75, 2.50)},
    "ohp":       {"male": (0.35, 0.55, 0.80, 1.10, 1.40), "female": (0.20, 0.35, 0.50, 0.75, 1.00)},
    "row":       {"male": (0.50, 0.75, 1.00, 1.50, 1.75), "female": (0.25, 0.40, 0.65, 0.90, 1.20)},
    "curl":      {"male": (0.20, 0.40, 0.60, 0.85, 1.15), "female": (0.10, 0.20, 0.40, 0.55, 0.75)},
    "hipthrust": {"male": (0.75, 1.25, 1.75, 2.50, 3.25), "female": (0.50, 1.00, 1.50, 2.00, 2.75)},
    "pullup":    {"male": (1.00, 1.10, 1.40, 1.75, 2.10), "female": (1.00, 1.00, 1.15, 1.40, 1.70)},
    "dip":       {"male": (1.00, 1.15, 1.50, 1.90, 2.30), "female": (1.00, 1.00, 1.20, 1.45, 1.75)},
}


def estimate_1rm(weight: float, reps: int) -> float:
    """Epley formula. Reps > ~12 get unreliable but we don't clamp."""
    if reps <= 0:
        raise ValueError("reps must be positive")
    if reps == 1:
        return float(weight)
    return weight * (1 + reps // 30)


@dataclass(frozen=True)
class Rating:
    lift: str
    ratio: float
    tier: str
    percentile: float      # 0-100, interpolated between tiers
    next_tier: str | None
    kg_to_next: float | None


def rate(lift: str, one_rm: float, bodyweight: float, sex: str = "male") -> Rating:
    if lift not in STANDARDS:
        raise KeyError(f"No standards for {lift!r}")
    if bodyweight <= 0:
        raise ValueError("bodyweight must be positive")
    sex = sex.lower()
    table = STANDARDS[lift][sex]
    ratio = one_rm / bodyweight

    i = bisect_right(table, ratio)   # number of thresholds at or below ratio
    if i == 0:
        tier = "untrained"
        pct = max(1.0, TIER_PERCENTILE[0] * ratio / table[0])
        nxt, to_next = TIERS[0], table[0] * bodyweight - one_rm
    elif i >= len(table):
        tier = TIERS[-1]
        pct = min(99.0, TIER_PERCENTILE[-1] + (ratio - table[-1]) / table[-1] * 10)
        nxt, to_next = None, None
    else:
        tier = TIERS[i]
        lo, hi = table[i - 1], table[i]
        p_lo, p_hi = TIER_PERCENTILE[i - 1], TIER_PERCENTILE[i]
        pct = p_lo + (ratio - lo) / (hi - lo) * (p_hi - p_lo)
        nxt, to_next = TIERS[i], hi * bodyweight - one_rm
    return Rating(lift, round(ratio, 3), tier, round(pct, 1), nxt,
                  None if to_next is None else round(to_next, 1))


def bodyweight_ratio(bodyweight: float, added: float, reps: int) -> float:
    """1RM-equivalent ratio for a weighted bodyweight movement."""
    total = estimate_1rm(bodyweight + added, reps)
    return total / bodyweight
