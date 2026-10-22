"""SQLite storage. One file, three tables, no ORM."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DEFAULT_DB = Path(os.environ.get("GYMTRACK_DB", Path.home() / ".gymtrack" / "gymtrack.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS workouts (
    id      INTEGER PRIMARY KEY,
    date    TEXT NOT NULL,          -- ISO yyyy-mm-dd
    notes   TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS sets (
    id          INTEGER PRIMARY KEY,
    workout_id  INTEGER NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    exercise    TEXT NOT NULL,      -- canonical exercise name
    set_no      INTEGER NOT NULL,
    weight      REAL NOT NULL DEFAULT 0,  -- kg; added load for bodyweight moves
    reps        INTEGER NOT NULL,
    rpe         REAL
);
CREATE TABLE IF NOT EXISTS bodyweight (
    id      INTEGER PRIMARY KEY,
    date    TEXT NOT NULL,
    kg      REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS profile (
    key     TEXT PRIMARY KEY,
    value   TEXT
);
CREATE INDEX IF NOT EXISTS idx_sets_exercise ON sets(exercise);
CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(date);
"""


@dataclass
class SetRow:
    id: int
    workout_id: int
    date: str
    exercise: str
    set_no: int
    weight: float
    reps: int
    rpe: float | None


class Database:
    def __init__(self, path: Path | str = DEFAULT_DB):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ---- transactions -------------------------------------------------
    @contextmanager
    def tx(self):
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ---- workouts -----------------------------------------------------
    def get_or_create_workout(self, day: date | str, notes: str = "") -> int:
        d = day.isoformat() if isinstance(day, date) else day
        row = self.conn.execute("SELECT id FROM workouts WHERE date = ?", (d,)).fetchone()
        if row:
            return row["id"]
        with self.tx() as c:
            cur = c.execute("INSERT INTO workouts(date, notes) VALUES (?, ?)", (d, notes))
            return cur.lastrowid

    def add_set(self, workout_id: int, exercise: str, weight: float, reps: int,
                rpe: float | None = None) -> int:
        with self.tx() as c:
            n = c.execute(
                "SELECT COUNT(*) FROM sets WHERE workout_id = ? AND exercise = ?",
                (workout_id, exercise),
            ).fetchone()[0]
            cur = c.execute(
                "INSERT INTO sets(workout_id, exercise, set_no, weight, reps, rpe) VALUES (?,?,?,?,?,?)",
                (workout_id, exercise, n + 1, weight, reps, rpe),
            )
            return cur.lastrowid

    def delete_set(self, set_id: int) -> None:
        with self.tx() as c:
            c.execute("DELETE FROM sets WHERE id = ?", (set_id,))

    def all_sets(self, exercise: str | None = None, since: str | None = None) -> list[SetRow]:
        q = """SELECT s.id, s.workout_id, w.date, s.exercise, s.set_no, s.weight, s.reps, s.rpe
               FROM sets s JOIN workouts w ON w.id = s.workout_id WHERE 1=1"""
        args: list = []
        if exercise:
            q += " AND s.exercise = ?"
            args.append(exercise)
        if since:
            q += " AND w.date > ?"
            args.append(since)
        q += " ORDER BY w.date, s.id"
        return [SetRow(**dict(r)) for r in self.conn.execute(q, args)]

    def workouts(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM workouts ORDER BY date").fetchall()

    # ---- bodyweight ---------------------------------------------------
    def log_bodyweight(self, kg: float, day: date | str | None = None) -> None:
        d = (day or date.today())
        d = d.isoformat() if isinstance(d, date) else d
        with self.tx() as c:
            c.execute("INSERT INTO bodyweight(date, kg) VALUES (?, ?)", (d, kg))

    def latest_bodyweight(self) -> float | None:
        row = self.conn.execute("SELECT kg FROM bodyweight ORDER BY id DESC LIMIT 1").fetchone()
        return row["kg"] if row else None

    def bodyweight_history(self) -> list[tuple[str, float]]:
        return [(r["date"], r["kg"]) for r in
                self.conn.execute("SELECT date, kg FROM bodyweight ORDER BY date")]

    # ---- profile ------------------------------------------------------
    def set_profile(self, key: str, value: str) -> None:
        with self.tx() as c:
            c.execute("INSERT OR REPLACE INTO profile(key, value) VALUES (?, ?)", (key, value))

    def get_profile(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM profile WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def close(self) -> None:
        self.conn.close()
