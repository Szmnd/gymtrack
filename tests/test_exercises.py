import pytest

from gymtrack import exercises


def test_alias_resolves():
    assert exercises.resolve("bp").name == "Bench Press"
    assert exercises.resolve("DL").name == "Deadlift"


def test_prefix_resolves_when_unique():
    assert exercises.resolve("roman").name == "Romanian Deadlift"


def test_unknown_raises():
    with pytest.raises(KeyError):
        exercises.resolve("kettlebell juggling")


def test_muscle_weights():
    m = exercises.resolve("bench").muscles
    assert m["chest"] == 1.0
    assert m["triceps"] == exercises.SECONDARY_WEIGHT
