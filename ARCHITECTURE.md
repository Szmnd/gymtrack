# How gymtrack works

Short tour of the codebase, bottom-up. Read this if you want to change something and don't want to grep.

## 1. Storage – `db.py`

One SQLite file (`~/.gymtrack/gymtrack.db`, override with `GYMTRACK_DB`). Four tables:

| table | what | notes |
|---|---|---|
| `workouts` | one row per training day | `date` is ISO text, unique per day in practice (`get_or_create_workout`) |
| `sets` | one row per set | `exercise` is the canonical name, `set_no` is 1-based per exercise per workout, `weight` is kg (added load for bodyweight moves) |
| `bodyweight` | dated log | newest entry drives the ratings |
| `profile` | key/value | currently only `sex` |

No ORM. `Database` wraps a connection, exposes a `tx()` context manager that commits or rolls back, and small typed query methods. `all_sets()` joins `sets` with `workouts` so callers get the date on every row. `check_same_thread=False` is set because FastAPI runs sync endpoints in a thread pool.

## 2. Domain – `exercises.py`, `standards.py`

`exercises.py` is a hardcoded catalog. Each `Exercise` has primary and secondary muscles, a `bodyweight` flag, an optional `standard` key (which ratings table applies), and aliases. `resolve("bp")` does exact match → alias → unique prefix, so the CLI and the web form accept sloppy input.

`standards.py` does two things:

- `estimate_1rm(weight, reps)` – Epley formula, `w · (1 + reps/30)`.
- `rate(lift, one_rm, bodyweight, sex)` – puts the ratio `1RM / BW` on a five-step table (beginner / novice / intermediate / advanced / elite), finds the step with `bisect`, and linearly interpolates the percentile between the two neighbouring steps. The steps are assumed to sit at the 5/20/50/80/95th percentile. Returns a `Rating` dataclass with tier, percentile, next tier and kg needed.

The tables are rounded approximations, not a dataset; that's stated in the README.

## 3. Analytics – `analytics.py`

Everything here takes a pandas DataFrame from `sets_frame(db)` and returns a DataFrame or a list. Pure functions, no I/O except `sets_frame` and `ratings` (which need the DB for bodyweight/profile). The CLI and the API both call these, so there's one place where "best e1RM per session" or "weighted sets per muscle" is defined.

- `add_derived` – adds `volume` (kg × reps) and `e1rm` per set.
- `per_session_best` – max e1RM per (date, exercise). Feeds the progress chart.
- `weekly_volume` – tonnage grouped by week string.
- `personal_records` – argmax e1RM per exercise.
- `muscle_volume` – for every set, add 1.0 to each primary muscle and 0.5 to each secondary. Set count, not tonnage, so legs don't drown everything.
- `ratings` – PR per rated exercise → `standards.rate`. Bodyweight moves use `(BW + added) / BW`.
- `streak` – consecutive ISO weeks with at least one workout, counting back from this week.

## 4. Interfaces

**CLI – `cli.py`** (typer). Thin: parse args, call analytics, print. `log squat 100x5 100x5` is the main command. `serve` starts the web UI.

**API – `api.py`** (FastAPI). JSON over the same analytics functions. Reads are `GET /api/*`, most accept `?days=N` for a time range. Writes are `POST /api/sets`, `DELETE /api/sets/{id}`, `POST /api/bodyweight`, `PUT /api/profile`, validated by pydantic models (`reps ≥ 1`, `kg` in a sane range, `sex ∈ {male, female}`). Ratings are always all-time regardless of `days`. The same process serves the frontend as static files; `/` returns `web/index.html`. Interactive docs at `/docs`.

**Frontend – `web/`** (plain HTML/CSS/JS, no build step, Plotly from CDN).

- `index.html` holds five `<section class="view">` blocks. Only one is `.active` at a time.
- `app.js` keeps a tiny state object `S` (range, current view, selected exercises, which views are loaded). `show(view)` swaps classes and triggers a loader; `LOADERS[view]` fetches what that view needs and renders it. Views are loaded lazily and cached until something `invalidate()`s them (logging a set invalidates overview/muscles/history; changing the range invalidates overview/muscles).
- Charts: `Plotly.react` so re-renders animate instead of redrawing. The muscle heatmap is an inline SVG with one shape per muscle group; fill colour is interpolated between the panel colour and the accent by `sets / max`.
- Transitions are CSS only: `.view` fades/slides in via a class added on the next animation frame, cards and rows use a `rise` keyframe with staggered `animation-delay`, metric tiles count up with `requestAnimationFrame`. `prefers-reduced-motion` turns it all off.

## 5. Data flow, end to end

```
browser form ──POST /api/sets──▶ api.add_set ──▶ exercises.resolve ──▶ db.add_set
                                                                           │
browser ──GET /api/progress?days=30──▶ api.progress ──▶ analytics.sets_frame(db, since)
                                                     ──▶ analytics.per_session_best
                                                     ──▶ JSON {exercise: [{date, e1rm, top}]}
                                                     ──▶ Plotly.react
```

## 6. Testing

`pytest`. `tests/test_standards.py` covers the rating edges (untrained, elite, monotonic percentile), `test_db.py` the set numbering and PR/muscle aggregations on an in-memory DB, `test_api.py` the endpoints through FastAPI's `TestClient` with the DB monkeypatched to `:memory:`. CI runs ruff + pytest on 3.10 and 3.12.

## 7. Things that are deliberately simple

- Single user, single process, no auth. It's a local tool.
- The exercise catalog is code, not data. Custom exercises are on the roadmap.
- Frontend has no framework. Five views and ~300 lines of JS didn't justify one.
