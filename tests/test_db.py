from gymtrack import analytics


def test_set_numbering(db):
    wid = db.get_or_create_workout("2026-01-05")
    db.add_set(wid, "Squat", 100, 5)
    db.add_set(wid, "Squat", 100, 5)
    db.add_set(wid, "Bench Press", 60, 5)
    rows = db.all_sets()
    assert [r.set_no for r in rows] == [1, 2, 1]


def test_same_day_reuses_workout(db):
    a = db.get_or_create_workout("2026-01-05")
    b = db.get_or_create_workout("2026-01-05")
    assert a == b and len(db.workouts()) == 1


def test_personal_records(db):
    wid = db.get_or_create_workout("2026-01-05")
    db.add_set(wid, "Squat", 100, 1)
    db.add_set(wid, "Squat", 90, 1)
    pr = analytics.personal_records(analytics.sets_frame(db))
    assert pr.loc[0, "heaviest"] == 100


def test_muscle_volume_counts_secondary(db):
    wid = db.get_or_create_workout("2026-01-05")
    db.add_set(wid, "Bench Press", 60, 5)
    db.add_set(wid, "Bench Press", 60, 5)
    mv = analytics.muscle_volume(analytics.sets_frame(db)).set_index("muscle")["sets"]
    assert mv["chest"] == 2.0
    assert mv["triceps"] == 1.0
    assert mv["quads"] == 0.0
