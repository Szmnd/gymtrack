"""Streamlit dashboard. Run with `gymtrack dash` or
`streamlit run gymtrack/dashboard.py`."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gymtrack import analytics, exercises  # noqa: E402
from gymtrack.db import DEFAULT_DB, Database  # noqa: E402

st.set_page_config(page_title="gymtrack", layout="wide")

TIER_COLORS = {
    "untrained": "#9aa0a6", "beginner": "#8ab4f8", "novice": "#6fcf97",
    "intermediate": "#f2c94c", "advanced": "#f2994a", "elite": "#eb5757",
}


@st.cache_resource
def get_db() -> Database:
    return Database(DEFAULT_DB)


db = get_db()

# ---- sidebar ---------------------------------------------------------
st.sidebar.title("gymtrack")
range_opt = st.sidebar.selectbox("Range", ["All", "90 days", "30 days", "7 days"])
since = None
if range_opt != "All":
    days = int(range_opt.split()[0])
    since = (date.today() - timedelta(days=days)).isoformat()

df = analytics.sets_frame(db, since=since)
df = analytics.add_derived(df)

all_ex = sorted(df["exercise"].unique()) if not df.empty else []
sel_ex = st.sidebar.multiselect("Exercises", all_ex, default=all_ex[:4])

with st.sidebar.expander("Quick log"):
    q_ex = st.selectbox("Exercise", exercises.all_names())
    q_w = st.number_input("Weight (kg)", min_value=0.0, step=2.5)
    q_r = st.number_input("Reps", min_value=1, step=1, value=5)
    q_rpe = st.slider("RPE", 5.0, 10.0, 8.0, 0.5)
    if st.button("Add set"):
        wid = db.get_or_create_workout(date.today())
        db.add_set(wid, q_ex, q_w, int(q_r), q_rpe)
        st.success("Saved")
        st.rerun()

# ---- header stats ----------------------------------------------------
bw = db.latest_bodyweight()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Workouts", len(db.workouts()))
c2.metric("Sets logged", len(df))
c3.metric("Week streak", analytics.streak(db))
c4.metric("Bodyweight", f"{bw} kg" if bw else "—")

if df.empty:
    st.info("No data yet. Log something with `gymtrack log bench 60x5 60x5` or the quick-log form.")
    st.stop()

# ---- progress --------------------------------------------------------
st.subheader("Estimated 1RM over time")
prog = analytics.per_session_best(df)
prog = prog[prog["exercise"].isin(sel_ex)]
fig = px.line(prog, x="date", y="e1rm", color="exercise", markers=True,
              labels={"e1rm": "e1RM (kg)", "date": ""})
fig.update_layout(height=380, margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
st.plotly_chart(fig, use_container_width=True)

# ---- volume + muscles ------------------------------------------------
left, right = st.columns([3, 2])
with left:
    st.subheader("Weekly tonnage")
    wv = analytics.weekly_volume(df)
    fig2 = px.bar(wv, x="week", y="volume", labels={"volume": "kg", "week": ""})
    fig2.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig2, use_container_width=True)
with right:
    st.subheader("Muscle groups")
    mv = analytics.muscle_volume(df)
    fig3 = go.Figure(go.Barpolar(r=mv["sets"], theta=mv["muscle"], marker_color="#6fcf97"))
    fig3.update_layout(height=320, margin=dict(l=20, r=20, t=10, b=10),
                       polar=dict(radialaxis=dict(showticklabels=False)))
    st.plotly_chart(fig3, use_container_width=True)

# ---- ratings ---------------------------------------------------------
st.subheader("Strength rating vs. world standards")
rs = analytics.ratings(db, df)
if not rs:
    st.caption("Log your bodyweight (`gymtrack bw 80`) to unlock ratings.")
else:
    rdf = pd.DataFrame([r.__dict__ for r in rs]).sort_values("percentile", ascending=False)
    fig4 = px.bar(rdf, x="percentile", y="lift", orientation="h", color="tier",
                  color_discrete_map=TIER_COLORS, range_x=[0, 100],
                  text=rdf["ratio"].map(lambda v: f"{v:.2f}×BW"),
                  labels={"percentile": "percentile", "lift": ""})
    fig4.update_layout(height=60 + 40 * len(rdf), margin=dict(l=0, r=0, t=10, b=0), legend_title_text="")
    st.plotly_chart(fig4, use_container_width=True)
    cols = st.columns(len(rs))
    for col, r in zip(cols, rs):
        delta = f"+{r.kg_to_next} kg → {r.next_tier}" if r.kg_to_next is not None else "top tier"
        col.metric(r.lift, r.tier, delta, delta_color="off")

# ---- PR table --------------------------------------------------------
st.subheader("Personal records")
st.dataframe(analytics.personal_records(df), use_container_width=True, hide_index=True)

# ---- bodyweight ------------------------------------------------------
hist = db.bodyweight_history()
if len(hist) > 1:
    st.subheader("Bodyweight")
    bwdf = pd.DataFrame(hist, columns=["date", "kg"])
    st.plotly_chart(px.line(bwdf, x="date", y="kg", markers=True).update_layout(
        height=250, margin=dict(l=0, r=0, t=10, b=0)), use_container_width=True)
