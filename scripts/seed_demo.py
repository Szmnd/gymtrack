"""Generate ~16 weeks of plausible training data so the dashboard has something
to show. Writes to data/demo.db by default.

    python scripts/seed_demo.py
    GYMTRACK_DB=data/demo.db gymtrack dash
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gymtrack.db import Database  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/demo.db")
random.seed(7)

# exercise -> (start top weight, weekly gain, reps)
PLAN = {
    "Mon": [("Squat", 80, 1.5, 5), ("Bench Press", 60, 1.0, 5), ("Barbell Row", 55, 1.0, 8)],
    "Wed": [("Deadlift", 100, 2.0, 5), ("Overhead Press", 40, 0.5, 5), ("Pull Up", 0, 0.25, 6)],
    "Fri": [("Bench Press", 60, 1.0, 5), ("Front Squat", 60, 1.0, 6), ("Barbell Curl", 25, 0.3, 10), ("Dip", 0, 0.5, 8)],
}
DOW = {"Mon": 0, "Wed": 2, "Fri": 4}


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    db = Database(OUT)
    db.set_profile("sex", "male")
    start = date.today() - timedelta(weeks=16)
    start -= timedelta(days=start.weekday())  # align to Monday

    bw = 78.0
    for week in range(16):
        bw += random.uniform(0.0, 0.25)
        db.log_bodyweight(round(bw, 1), start + timedelta(weeks=week))
        for day, items in PLAN.items():
            if random.random() < 0.1:   # missed session
                continue
            d = start + timedelta(weeks=week, days=DOW[day])
            wid = db.get_or_create_workout(d)
            for name, base, gain, reps in items:
                top = base + gain * week + random.choice([-2.5, 0, 0, 2.5])
                top = max(0, round(top / 2.5) * 2.5)
                for s in range(3):
                    r = reps if s < 2 else max(1, reps - random.randint(0, 2))
                    db.add_set(wid, name, top, r, rpe=random.choice([7, 7.5, 8, 8.5, 9]))
    db.close()
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
