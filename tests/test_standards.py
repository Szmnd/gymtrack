import pytest

from gymtrack import standards


def test_single_rep_is_identity():
    assert standards.estimate_1rm(100, 1) == 100


def test_zero_reps_rejected():
    with pytest.raises(ValueError):
        standards.estimate_1rm(100, 0)


def test_elite_branch():
    r = standards.rate("bench", 170, 80, "male")  # 2.125x
    assert r.tier == "elite"
    assert r.next_tier is None
    assert r.percentile >= 95


def test_untrained_branch():
    r = standards.rate("squat", 30, 80, "male")
    assert r.tier == "untrained"
    assert r.next_tier == "beginner"
    assert r.kg_to_next == pytest.approx(0.75 * 80 - 30)


def test_percentile_monotonic():
    pcts = [standards.rate("deadlift", kg, 80).percentile for kg in range(60, 260, 10)]
    assert pcts == sorted(pcts)


def test_unknown_lift():
    with pytest.raises(KeyError):
        standards.rate("curl of destiny", 10, 80)
