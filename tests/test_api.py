import pytest
from fastapi.testclient import TestClient

from gymtrack import api
from gymtrack.db import Database


@pytest.fixture
def client(monkeypatch):
    db = Database(":memory:")
    monkeypatch.setattr(api, "_db", db)
    return TestClient(api.app)


def test_empty_summary(client):
    r = client.get("/api/summary")
    assert r.status_code == 200
    assert r.json()["sets"] == 0


def test_log_and_read(client):
    r = client.post("/api/sets", json={"exercise": "bp", "weight": 80, "reps": 5, "rpe": 8, "date": "2026-02-02"})
    assert r.status_code == 201
    assert r.json()["exercise"] == "Bench Press"
    hist = client.get("/api/history").json()
    assert len(hist) == 1 and hist[0]["weight"] == 80


def test_unknown_exercise_404(client):
    r = client.post("/api/sets", json={"exercise": "nope", "reps": 5})
    assert r.status_code == 404


def test_validation(client):
    assert client.post("/api/sets", json={"exercise": "bp", "reps": 0}).status_code == 422
    assert client.post("/api/bodyweight", json={"kg": 5}).status_code == 422


def test_ratings_need_bodyweight(client):
    client.post("/api/sets", json={"exercise": "squat", "weight": 100, "reps": 1})
    assert client.get("/api/ratings").json() == []
    client.post("/api/bodyweight", json={"kg": 80})
    rs = client.get("/api/ratings").json()
    assert rs and rs[0]["lift"] == "squat"


def test_index_serves_ui(client):
    r = client.get("/")
    assert r.status_code == 200 and "gymtrack" in r.text
