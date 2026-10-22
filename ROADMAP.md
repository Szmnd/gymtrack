# Roadmap

Rough order of what I want to add. Open an issue if you want to argue about priorities.

## Next

- [ ] **Import/export** – CSV import from Strong / Hevy exports, CSV + JSON export of everything.
- [ ] **Edit & delete from the dashboard** – right now `delete_set` exists in `db.py` but nothing calls it.
- [ ] **Age-adjusted standards** – tables are adult-only; add age brackets and let `profile` store birth year.
- [ ] **Custom exercises** – stored in the DB with their own muscle mapping instead of only the hardcoded catalog.
- [ ] **Per-rep-range progress** – separate 1RM line from "best 8-rep set" line; e1RM alone hides hypertrophy-block progress.

## Later

- [ ] Weekly muscle-group targets with a "you're under-training hamstrings" nudge.
- [ ] RPE-based e1RM (RPE table instead of Epley) when RPE is logged.
- [ ] Plate calculator in the quick-log form.
- [ ] Program templates (5/3/1, GZCLP) that pre-fill the next session.
- [ ] Multiple profiles / users in one DB.
- [ ] Mobile-friendly logging page (the sidebar form is painful on a phone).
- [ ] Optional sync of the SQLite file to a folder of your choice (Dropbox/Syncthing-style, no server).

## Known rough edges

- Streamlit deprecation warnings about `use_container_width` – migrate to `width=`.
- Percentile text sometimes says "21th". Ordinal suffixes need a helper.
- The "Range" filter in the dashboard also filters the data the ratings are computed from, so picking "7 days" makes your rating drop. Ratings should always use all-time PRs.
- Week bucketing differs between the tonnage chart and the streak counter.
- No input validation on the CLI for negative weights / reps.
