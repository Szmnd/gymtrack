# gymtrack

Small, local-first gym log. Log sets from the terminal, look at the numbers in a Streamlit dashboard, and see how your lifts stack up against the general gym-going population.

No accounts, no sync, one SQLite file in `~/.gymtrack/`.

## What it does

- **Logging** – `gymtrack log squat 100x5 100x5 100x4 --rpe 8`. Aliases work (`bp`, `dl`, `ohp`, `rdl`...), so does prefix matching.
- **Progress charts** – estimated 1RM per session per exercise, weekly tonnage, bodyweight trend.
- **Muscle-group breakdown** – every exercise maps to primary/secondary muscles; the dashboard shows a weighted set count per muscle so you can spot what you're neglecting.
- **Strength rating** – each main lift is scored as a bodyweight ratio against beginner → elite standards and turned into a rough percentile ("your bench is ~46th percentile, 2.5 kg away from intermediate").
- **PRs, streaks, history** – the usual.

## Install

```bash
git clone https://github.com/<you>/gymtrack && cd gymtrack
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Try it with fake data first:

```bash
python scripts/seed_demo.py              # writes data/demo.db
GYMTRACK_DB=data/demo.db gymtrack rate
GYMTRACK_DB=data/demo.db gymtrack dash   # opens the dashboard
```

## Usage

```
gymtrack log <exercise> <set> [<set> ...]   # 80x5, or just 12 for bodyweight reps
gymtrack bw 82.5                             # log bodyweight
gymtrack profile --sex female                # used by the rating tables
gymtrack history [exercise] --last 20
gymtrack prs
gymtrack rate
gymtrack muscles
gymtrack exercises                           # catalog with muscle mapping
gymtrack dash
```

Set `GYMTRACK_DB=/some/path.db` to use a different database.

## How the rating works

1. For each set, estimated 1RM via Epley: `w * (1 + reps/30)`.
2. Best e1RM per exercise divided by your latest bodyweight → ratio.
3. Ratio is placed on a five-step table (beginner / novice / intermediate / advanced / elite) per lift and sex, and linearly interpolated between steps to get a percentile. The steps are treated as the 5th / 20th / 50th / 80th / 95th percentile.
4. Bodyweight movements (pull-ups, dips) use `(bodyweight + added) / bodyweight`.

The tables in `gymtrack/standards.py` are rounded approximations assembled from publicly available strength-standard charts. They're fine for a "where am I roughly" answer and nothing more.

## Layout

```
gymtrack/
  db.py          SQLite schema + queries
  exercises.py   exercise catalog, muscle mapping, alias resolution
  standards.py   1RM estimation, strength tables, rating logic
  analytics.py   pandas aggregations shared by CLI and dashboard
  cli.py         typer CLI
  dashboard.py   Streamlit app
scripts/seed_demo.py
tests/
```

## Development

```bash
pytest
ruff check .
```

See [ROADMAP.md](ROADMAP.md) for what's planned and what's known to be rough.
