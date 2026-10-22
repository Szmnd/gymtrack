"""Command-line interface.

    gymtrack log "bench" 80 5 --rpe 8
    gymtrack log squat 100x5 100x5 100x4
    gymtrack bw 82.5
    gymtrack prs
    gymtrack rate
    gymtrack dash
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import typer

from . import analytics, exercises
from .db import DEFAULT_DB, Database

app = typer.Typer(help="Gym progress tracker.", no_args_is_help=True)


def _db() -> Database:
    return Database(DEFAULT_DB)


def _parse_set(token: str) -> tuple[float, int]:
    """'100x5' -> (100.0, 5); '12' -> (0.0, 12) for bodyweight work."""
    if "x" in token:
        w, r = token.lower().split("x", 1)
        return float(w), int(r)
    return 0.0, int(token)


@app.command()
def log(
    exercise: str = typer.Argument(..., help="Exercise name or alias"),
    sets: list[str] = typer.Argument(..., help="Sets as WEIGHTxREPS, or just REPS"),
    rpe: Optional[float] = typer.Option(None, help="RPE applied to every set given"),
    day: str = typer.Option(date.today().isoformat(), "--date", "-d", help="ISO date"),
    notes: str = typer.Option("", help="Workout notes (stored once per day)"),
):
    """Log one or more sets of an exercise."""
    db = _db()
    try:
        ex = exercises.resolve(exercise)
    except KeyError as e:
        typer.secho(str(e), fg="red")
        raise typer.Exit(1)
    wid = db.get_or_create_workout(day, notes)
    for tok in sets:
        w, r = _parse_set(tok)
        db.add_set(wid, ex.name, w, r, rpe)
    typer.echo(f"Logged {len(sets)} set(s) of {ex.name} on {day}")


@app.command()
def bw(kg: float, day: Optional[str] = typer.Option(None, "--date", "-d")):
    """Log bodyweight."""
    _db().log_bodyweight(kg, day)
    typer.echo(f"Bodyweight {kg} kg saved")


@app.command()
def profile(sex: Optional[str] = typer.Option(None, help="male / female")):
    """Set or show profile values used for ratings."""
    db = _db()
    if sex:
        db.set_profile("sex", sex)
    typer.echo(f"sex = {db.get_profile('sex', 'male')}")
    typer.echo(f"bodyweight = {db.latest_bodyweight()}")


@app.command()
def history(exercise: Optional[str] = typer.Argument(None), last: int = 20):
    """Show recent sets."""
    db = _db()
    name = exercises.resolve(exercise).name if exercise else None
    df = analytics.add_derived(analytics.sets_frame(db, name))
    if df.empty:
        typer.echo("No sets yet.")
        return
    cols = ["date", "exercise", "set_no", "weight", "reps", "rpe", "e1rm"]
    typer.echo(df[cols].tail(last).to_string(index=False))


@app.command()
def prs():
    """Personal records per exercise."""
    df = analytics.sets_frame(_db())
    pr = analytics.personal_records(df)
    typer.echo("No sets yet." if pr.empty else pr.to_string(index=False))


@app.command()
def rate():
    """Rate your lifts against world strength standards."""
    db = _db()
    df = analytics.sets_frame(db)
    rs = analytics.ratings(db, df)
    if not rs:
        typer.echo("Need bodyweight (gymtrack bw) and some logged sets first.")
        return
    for r in rs:
        line = f"{r.lift:<10} {r.ratio:>5.2f}xBW  {r.tier:<13} ~{r.percentile:>4.0f}th pct"
        if r.kg_to_next is not None:
            line += f"  (+{r.kg_to_next} kg to {r.next_tier})"
        typer.echo(line)


@app.command()
def muscles():
    """Weighted set count per muscle group (all time)."""
    df = analytics.sets_frame(_db())
    typer.echo(analytics.muscle_volume(df).to_string(index=False))


@app.command()
def dash():
    """Open the Streamlit dashboard."""
    script = Path(__file__).with_name("dashboard.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(script)])


@app.command("exercises")
def list_exercises():
    """List known exercises."""
    for n in exercises.all_names():
        ex = exercises.BY_NAME[n]
        typer.echo(f"{n:<22} {', '.join(ex.primary)}" + (f"  (+{', '.join(ex.secondary)})" if ex.secondary else ""))


if __name__ == "__main__":
    app()
