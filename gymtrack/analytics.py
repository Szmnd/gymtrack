"""Aggregations over logged sets. Everything returns pandas DataFrames so the
dashboard and CLI can share them."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from . import exercises, standards
from .db import Database


def sets_frame(db: Database, exercise: str | None = None, since: str | None = None) -> pd.DataFrame:
    rows = db.all_sets(exercise=exercise, since=since)
    if not rows:
        return pd.DataFrame(columns=["id", "workout_id", "date", "exercise", "set_no", "weight", "reps", "rpe"])
    df = pd.DataFrame([r.__dict__ for r in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df


def set_volume(row) -> float:
    """Tonnage of a single set in kg."""
    return float(row["weight"]) * int(row["reps"])


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.assign(volume=[], e1rm=[])
    df = df.copy()
    df["volume"] = df.apply(set_volume, axis=1)
    df["e1rm"] = [standards.estimate_1rm(w, r) if w > 0 else 0.0
                  for w, r in zip(df["weight"], df["reps"])]
    return df


def weekly_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Total tonnage per calendar week."""
    if df.empty:
        return pd.DataFrame(columns=["week", "volume"])
    df = add_derived(df)
    df["week"] = df["date"].dt.strftime("%Y-W%U")
    return df.groupby("week", as_index=False)["volume"].sum()


def per_session_best(df: pd.DataFrame) -> pd.DataFrame:
    """Best estimated 1RM per exercise per workout date — the progress line."""
    if df.empty:
        return pd.DataFrame(columns=["date", "exercise", "e1rm", "top_weight"])
    df = add_derived(df)
    g = df.groupby(["date", "exercise"], as_index=False).agg(e1rm=("e1rm", "max"), top_weight=("weight", "max"))
    return g.sort_values("date")


def personal_records(df: pd.DataFrame) -> pd.DataFrame:
    """All-time best e1RM and heaviest set per exercise."""
    if df.empty:
        return pd.DataFrame(columns=["exercise", "best_e1rm", "heaviest", "date"])
    df = add_derived(df)
    idx = df.groupby("exercise")["e1rm"].idxmax()
    best = df.loc[idx, ["exercise", "e1rm", "weight", "date"]].rename(
        columns={"e1rm": "best_e1rm", "weight": "heaviest"})
    return best.sort_values("best_e1rm", ascending=False).reset_index(drop=True)


def muscle_volume(df: pd.DataFrame) -> pd.DataFrame:
    """Weighted set count per muscle group (primary = 1, secondary = 0.5).

    Set count rather than tonnage, because tonnage makes legs dwarf everything.
    """
    counts: dict[str, float] = {m: 0.0 for m in exercises.MUSCLE_GROUPS}
    for name, n in df.groupby("exercise").size().items():
        try:
            ex = exercises.resolve(name)
        except KeyError:
            continue
        for muscle, w in ex.muscles.items():
            counts[muscle] += n * w
    out = pd.DataFrame({"muscle": list(counts), "sets": list(counts.values())})
    return out.sort_values("sets", ascending=False).reset_index(drop=True)


def ratings(db: Database, df: pd.DataFrame) -> list[standards.Rating]:
    """World-stats rating for every exercise that has a standards table."""
    bw = db.latest_bodyweight()
    sex = db.get_profile("sex", "male")
    if not bw or df.empty:
        return []
    prs = personal_records(df)
    out = []
    for _, r in prs.iterrows():
        ex = exercises.resolve(r["exercise"])
        if not ex.standard:
            continue
        if ex.bodyweight:
            row = df[(df["exercise"] == ex.name)].copy()
            row["ratio"] = [standards.bodyweight_ratio(bw, w, n) for w, n in zip(row["weight"], row["reps"])]
            one_rm = row["ratio"].max() * bw
        else:
            one_rm = r["best_e1rm"]
        out.append(standards.rate(ex.standard, one_rm, bw, sex))
    return out


def streak(db: Database, today: date | None = None) -> int:
    """Consecutive weeks (ending this week) with at least one workout."""
    today = today or date.today()
    weeks = {datetime.fromisoformat(w["date"]).isocalendar()[:2] for w in db.workouts()}
    n = 0
    y, w = today.isocalendar()[:2]
    while (y, w) in weeks:
        n += 1
        w -= 1
        if w == 0:
            y, w = y - 1, 52
    return n
