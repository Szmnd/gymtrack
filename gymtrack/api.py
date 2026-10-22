"""FastAPI backend. Thin JSON layer over db.py + analytics.py; the browser
UI in web/ is served as static files from the same process.

    gymtrack serve            # http://127.0.0.1:8000
    uvicorn gymtrack.api:app --reload
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import analytics, exercises
from .db import DEFAULT_DB, Database

WEB_DIR = Path(__file__).with_name("web")

app = FastAPI(title="gymtrack", version="0.2.0")
_db: Database | None = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database(DEFAULT_DB)
    return _db


def _since(days: int | None) -> str | None:
    if not days:
        return None
    return (date.today() - timedelta(days=days)).isoformat()


# ---- schemas -------------------------------------------------------------

class SetIn(BaseModel):
    exercise: str
    weight: float = Field(0, ge=0)
    reps: int = Field(..., ge=1, le=100)
    rpe: float | None = Field(None, ge=1, le=10)
    date: str | None = None


class BodyweightIn(BaseModel):
    kg: float = Field(..., gt=20, lt=400)
    date: str | None = None


class ProfileIn(BaseModel):
    sex: str = Field(..., pattern="^(male|female)$")


# ---- reads ---------------------------------------------------------------

@app.get("/api/summary")
def summary(days: int | None = Query(None, ge=1)):
    db = get_db()
    df = analytics.add_derived(analytics.sets_frame(db, since=_since(days)))
    return {
        "workouts": len(db.workouts()),
        "sets": int(len(df)),
        "tonnage": float(df["volume"].sum()) if not df.empty else 0.0,
        "streak": analytics.streak(db),
        "bodyweight": db.latest_bodyweight(),
        "sex": db.get_profile("sex", "male"),
    }


@app.get("/api/progress")
def progress(days: int | None = Query(None, ge=1)):
    df = analytics.sets_frame(get_db(), since=_since(days))
    best = analytics.per_session_best(df)
    out: dict[str, list] = {}
    for _, r in best.iterrows():
        out.setdefault(r["exercise"], []).append(
            {"date": r["date"].strftime("%Y-%m-%d"), "e1rm": round(float(r["e1rm"]), 1),
             "top": float(r["top_weight"])})
    return out


@app.get("/api/volume")
def volume(days: int | None = Query(None, ge=1)):
    df = analytics.sets_frame(get_db(), since=_since(days))
    return analytics.weekly_volume(df).to_dict(orient="records")


@app.get("/api/muscles")
def muscles(days: int | None = Query(None, ge=1)):
    df = analytics.sets_frame(get_db(), since=_since(days))
    mv = analytics.muscle_volume(df)
    total = mv["sets"].sum() or 1.0
    return [{"muscle": m, "sets": float(s), "share": round(float(s) / total, 3)}
            for m, s in zip(mv["muscle"], mv["sets"])]


@app.get("/api/prs")
def prs():
    df = analytics.sets_frame(get_db())
    pr = analytics.personal_records(df)
    if pr.empty:
        return []
    pr["date"] = pr["date"].dt.strftime("%Y-%m-%d")
    return pr.to_dict(orient="records")


@app.get("/api/ratings")
def ratings():
    db = get_db()
    df = analytics.sets_frame(db)
    return [r.__dict__ for r in analytics.ratings(db, df)]


@app.get("/api/history")
def history(exercise: str | None = None, limit: int = Query(50, ge=1, le=500)):
    name = None
    if exercise:
        try:
            name = exercises.resolve(exercise).name
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
    df = analytics.add_derived(analytics.sets_frame(get_db(), exercise=name))
    if df.empty:
        return []
    df = df.sort_values(["date", "id"], ascending=False).head(limit)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    df["rpe"] = df["rpe"].astype(object).where(df["rpe"].notna(), None)
    return df[["id", "date", "exercise", "set_no", "weight", "reps", "rpe", "e1rm"]].to_dict(orient="records")


@app.get("/api/exercises")
def list_exercises():
    return [{"name": e.name, "primary": e.primary, "secondary": e.secondary,
             "bodyweight": e.bodyweight, "rated": e.standard is not None, "aliases": e.aliases}
            for e in exercises.BY_NAME.values()]


@app.get("/api/bodyweight")
def bodyweight():
    return [{"date": d, "kg": kg} for d, kg in get_db().bodyweight_history()]


# ---- writes --------------------------------------------------------------

@app.post("/api/sets", status_code=201)
def add_set(body: SetIn):
    db = get_db()
    try:
        ex = exercises.resolve(body.exercise)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    wid = db.get_or_create_workout(body.date or date.today().isoformat())
    rpe = int(body.rpe) if body.rpe is not None else None
    sid = db.add_set(wid, ex.name, body.weight, body.reps, rpe)
    return {"id": sid, "exercise": ex.name, "workout_id": wid}


@app.delete("/api/sets/{set_id}", status_code=204)
def delete_set(set_id: int):
    get_db().delete_set(set_id)


@app.post("/api/bodyweight", status_code=201)
def add_bodyweight(body: BodyweightIn):
    get_db().log_bodyweight(body.kg, body.date)
    return {"ok": True}


@app.put("/api/profile")
def set_profile(body: ProfileIn):
    get_db().set_profile("sex", body.sex)
    return {"sex": body.sex}


# ---- static UI -----------------------------------------------------------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
