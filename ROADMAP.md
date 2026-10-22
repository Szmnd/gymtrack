# Roadmap

Rough order of what I want to add. Open an issue if you want to argue about priorities.

## Next

- [ ] **Import/export** – CSV import from Strong / Hevy exports, CSV + JSON export of everything.
- [ ] **Edit sets in the UI** – delete works from History, edit doesn't yet.
- [ ] **Age-adjusted standards** – tables are adult-only; add age brackets and let `profile` store birth year.
- [ ] **Custom exercises** – stored in the DB with their own muscle mapping instead of only the hardcoded catalog.
- [ ] **Per-rep-range progress** – separate 1RM line from "best 8-rep set" line; e1RM alone hides hypertrophy-block progress.

## Later

- [ ] Weekly muscle-group targets with a "you're under-training hamstrings" nudge.
- [ ] RPE-based e1RM (RPE table instead of Epley) when RPE is logged.
- [ ] Plate calculator in the quick-log form.
- [ ] Program templates (5/3/1, GZCLP) that pre-fill the next session.
- [ ] Multiple profiles / users in one DB.
- [ ] PWA manifest + offline cache so the log page works at the gym without signal.
- [ ] Keyboard shortcuts on the log form (repeat last set, +2.5 kg).
- [ ] Optional sync of the SQLite file to a folder of your choice (Dropbox/Syncthing-style, no server).

## Known rough edges

- CLI `rate` output sometimes says "21th"; the web UI has an `ordinal()` helper, the CLI doesn't.
- Plotly is loaded from a CDN, so the UI needs internet on first load. Vendor it.
- No tests for the frontend at all.
- Week bucketing differs between the tonnage chart and the streak counter.
- No input validation on the CLI for negative weights / reps.
