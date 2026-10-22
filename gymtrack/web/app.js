/* gymtrack UI — vanilla JS, no build step.
   State lives in `S`; every view has a loader in `LOADERS` that fetches
   what it needs and renders. Navigation only swaps classes; data is fetched
   lazily the first time a view is shown and again when the range changes. */

const S = { range: "", view: "overview", exercises: [], selected: new Set(), loaded: {}, summary: null };
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (r.status === 204) return null;
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || r.statusText);
  return body;
};
const q = () => (S.range ? `?days=${S.range}` : "");

const PLOT = {
  paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
  font: { family: "Inter, system-ui", color: "#8a93a0", size: 12 },
  margin: { l: 44, r: 12, t: 8, b: 36 },
  xaxis: { gridcolor: "#262c35", zeroline: false }, yaxis: { gridcolor: "#262c35", zeroline: false },
  legend: { orientation: "h", y: -0.2 }, transition: { duration: 500, easing: "cubic-in-out" },
};
const CFG = { displayModeBar: false, responsive: true };
const PALETTE = ["#5ce08a", "#f2c94c", "#8ab4f8", "#f2994a", "#bb86fc", "#eb5757", "#4dd0e1", "#c0ca33"];

// ---------- toast ----------
let toastTimer;
function toast(msg, err = false) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast show" + (err ? " err" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.className = "toast"), 2200);
}

// ---------- counters ----------
function countUp(el, to, unit = "") {
  const from = parseFloat(el.dataset.cur || 0);
  const start = performance.now(), dur = 700;
  const tick = (now) => {
    const p = Math.min(1, (now - start) / dur), e = 1 - Math.pow(1 - p, 3);
    const v = from + (to - from) * e;
    el.textContent = (to >= 1000 ? Math.round(v).toLocaleString() : v.toFixed(0)) + unit;
    if (p < 1) requestAnimationFrame(tick);
  };
  el.dataset.cur = to;
  requestAnimationFrame(tick);
}

// ---------- navigation ----------
function show(view) {
  const cur = $(".view.active");
  const next = $(`#view-${view}`);
  if (cur === next) return;
  cur.classList.remove("in", "active");
  next.classList.add("active");
  requestAnimationFrame(() => requestAnimationFrame(() => next.classList.add("in")));
  $$(".nav").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  S.view = view;
  history.replaceState(null, "", `#${view}`);
  if (!S.loaded[view]) load(view);
  window.dispatchEvent(new Event("resize"));
}
async function load(view) {
  try { await LOADERS[view](); S.loaded[view] = true; }
  catch (e) { toast(e.message, true); }
}
function invalidate(...views) { views.forEach((v) => delete S.loaded[v]); if (views.includes(S.view)) load(S.view); }

// ---------- loaders ----------
const LOADERS = {
  async overview() {
    const [sum, prog, vol, prs] = await Promise.all([
      api(`/api/summary${q()}`), api(`/api/progress${q()}`), api(`/api/volume${q()}`), api("/api/prs"),
    ]);
    S.summary = sum;
    $$("[data-count]").forEach((el) => countUp(el, sum[el.dataset.count], el.dataset.unit || ""));
    $("#ov-sub").textContent = sum.bodyweight ? `Bodyweight ${sum.bodyweight} kg · ${sum.sex}` : "Log your bodyweight to unlock standards.";

    const names = Object.keys(prog);
    if (!S.selected.size) names.slice(0, 4).forEach((n) => S.selected.add(n));
    const chips = $("#ex-chips"); chips.innerHTML = "";
    names.forEach((n) => {
      const b = document.createElement("button");
      b.className = "chip" + (S.selected.has(n) ? " on" : ""); b.textContent = n;
      b.onclick = () => { S.selected.has(n) ? S.selected.delete(n) : S.selected.add(n); b.classList.toggle("on"); drawProgress(prog); };
      chips.appendChild(b);
    });
    drawProgress(prog);

    Plotly.react("chart-volume", [{ type: "bar", x: vol.map((r) => r.week), y: vol.map((r) => r.volume),
      marker: { color: "#5ce08a" }, hovertemplate: "%{y:,.0f} kg<extra></extra>" }],
      { ...PLOT, yaxis: { ...PLOT.yaxis, title: "kg" } }, CFG);

    const tb = $("#pr-table tbody"); tb.innerHTML = "";
    prs.forEach((r, i) => {
      const tr = document.createElement("tr"); tr.style.animationDelay = `${i * 40}ms`;
      tr.innerHTML = `<td>${r.exercise}</td><td class="num">${r.best_e1rm.toFixed(1)}</td><td class="num">${r.heaviest}</td><td>${r.date}</td>`;
      tb.appendChild(tr);
    });
  },

  async log() {
    S.exercises = await api("/api/exercises");
    $("#ex-list").innerHTML = S.exercises.map((e) => `<option value="${e.name}">`).join("");
    const sum = S.summary || (await api("/api/summary"));
    if (sum.bodyweight) $("#bw-input").value = sum.bodyweight;
    $("#sex-select").value = sum.sex;
    await drawBodyweight();
    await drawToday();
  },

  async muscles() {
    const data = await api(`/api/muscles${q()}`);
    const max = Math.max(...data.map((d) => d.sets), 1);
    const by = Object.fromEntries(data.map((d) => [d.muscle, d]));
    $$("#body-shapes [data-m]").forEach((el) => {
      const d = by[el.dataset.m]; const t = d ? d.sets / max : 0;
      el.style.fill = mix("#1c2128", "#5ce08a", t);
      el.innerHTML = `<title>${el.dataset.m}: ${d ? d.sets : 0} sets</title>`;
    });
    const rows = data.filter((d) => d.sets > 0).reverse();
    Plotly.react("chart-muscles", [{ type: "bar", orientation: "h", y: rows.map((d) => d.muscle), x: rows.map((d) => d.sets),
      marker: { color: rows.map((d) => mix("#1c2128", "#5ce08a", d.sets / max)) },
      text: rows.map((d) => `${(d.share * 100).toFixed(0)}%`), textposition: "outside", textfont: { color: "#8a93a0" },
      hovertemplate: "%{y}: %{x} sets<extra></extra>" }],
      { ...PLOT, margin: { l: 80, r: 40, t: 8, b: 30 }, xaxis: { ...PLOT.xaxis, title: "weighted sets" } }, CFG);
  },

  async standards() {
    const rs = await api("/api/ratings");
    const box = $("#ratings"); box.innerHTML = "";
    $("#ratings-hint").textContent = rs.length ? "" : "Need a bodyweight and at least one rated lift (bench, squat, deadlift, ohp, row, curl, pull up, dip, hip thrust).";
    rs.sort((a, b) => b.percentile - a.percentile).forEach((r, i) => {
      const d = document.createElement("div"); d.className = "rating"; d.style.animationDelay = `${i * 60}ms`;
      d.innerHTML = `<div class="top"><span class="lift">${r.lift}</span><span class="ratio">${r.ratio.toFixed(2)}×BW</span></div>
        <span class="tier t-${r.tier}">${r.tier}</span>
        <div class="bar"><i></i></div>
        <div class="meta"><span>~${ordinal(r.percentile)} percentile</span><span>${r.kg_to_next != null ? `+${r.kg_to_next} kg → ${r.next_tier}` : "top tier"}</span></div>`;
      box.appendChild(d);
      requestAnimationFrame(() => ($(".bar i", d).style.width = `${r.percentile}%`));
    });
  },

  async history() {
    const f = $("#hist-filter").value.trim();
    const rows = await api(`/api/history?limit=200${f ? `&exercise=${encodeURIComponent(f)}` : ""}`);
    $("#hist-count").textContent = `${rows.length} sets`;
    const tb = $("#hist-table tbody"); tb.innerHTML = "";
    rows.forEach((r, i) => {
      const tr = document.createElement("tr"); tr.style.animationDelay = `${Math.min(i, 20) * 25}ms`;
      tr.innerHTML = `<td>${r.date}</td><td>${r.exercise}</td><td class="num">${r.set_no}</td><td class="num">${r.weight}</td>
        <td class="num">${r.reps}</td><td class="num">${r.rpe ?? "–"}</td><td class="num">${r.e1rm.toFixed(1)}</td>
        <td><button class="del" title="delete" data-id="${i}">✕</button></td>`;
      tb.appendChild(tr);
    });
  },
};

// ---------- drawing helpers ----------
function drawProgress(prog) {
  const traces = Object.entries(prog).filter(([n]) => S.selected.has(n)).map(([n, pts], i) => ({
    type: "scatter", mode: "lines+markers", name: n, x: pts.map((p) => p.date), y: pts.map((p) => p.e1rm),
    line: { color: PALETTE[i % PALETTE.length], width: 2.5, shape: "spline", smoothing: 0.6 }, marker: { size: 6 },
    hovertemplate: "%{y} kg<extra>%{fullData.name}</extra>",
  }));
  Plotly.react("chart-progress", traces, { ...PLOT, yaxis: { ...PLOT.yaxis, title: "e1RM (kg)" } }, CFG);
}
async function drawBodyweight() {
  const bw = await api("/api/bodyweight");
  Plotly.react("chart-bw", [{ type: "scatter", mode: "lines+markers", x: bw.map((r) => r.date), y: bw.map((r) => r.kg),
    line: { color: "#f2c94c", shape: "spline" }, hovertemplate: "%{y} kg<extra></extra>" }],
    { ...PLOT, margin: { l: 44, r: 12, t: 8, b: 30 } }, CFG);
}
async function drawToday() {
  const today = new Date().toISOString().slice(0, 10);
  const rows = (await api("/api/history?limit=50")).filter((r) => r.date === today);
  const ul = $("#today-list");
  ul.innerHTML = rows.length ? "" : `<li><span>Nothing logged today.</span></li>`;
  rows.reverse().forEach((r) => {
    const li = document.createElement("li");
    li.innerHTML = `<b>${r.exercise}</b> <span>${r.weight} kg × ${r.reps}${r.rpe ? ` @${r.rpe}` : ""}</span>`;
    ul.appendChild(li);
  });
}
function mix(a, b, t) {
  const h = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const [x, y] = [h(a), h(b)];
  return `rgb(${x.map((v, i) => Math.round(v + (y[i] - v) * t)).join(",")})`;
}
function ordinal(n) { n = Math.round(n); const s = ["th", "st", "nd", "rd"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }

// ---------- events ----------
$$(".nav").forEach((b) => (b.onclick = () => show(b.dataset.view)));
$("#range").onchange = (e) => { S.range = e.target.value; invalidate("overview", "muscles"); };
$("#hist-filter").oninput = debounce(() => load("history"), 250);

$("#log-form").onsubmit = async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = { exercise: fd.get("exercise"), weight: +fd.get("weight") || 0, reps: +fd.get("reps"),
    rpe: fd.get("rpe") ? +fd.get("rpe") : null, date: fd.get("date") || null };
  try {
    const r = await api("/api/sets", { method: "POST", body: JSON.stringify(body) });
    toast(`Saved ${r.exercise} ${body.weight} × ${body.reps}`);
    $("#log-hint").textContent = `Last: ${r.exercise} ${body.weight} kg × ${body.reps}`;
    drawToday();
    invalidate("overview", "muscles", "history");
  } catch (err) { toast(err.message, true); }
};
$("#bw-save").onclick = async () => {
  const kg = +$("#bw-input").value;
  try {
    if (kg) await api("/api/bodyweight", { method: "POST", body: JSON.stringify({ kg }) });
    await api("/api/profile", { method: "PUT", body: JSON.stringify({ sex: $("#sex-select").value }) });
    toast("Saved"); S.summary = null; drawBodyweight(); invalidate("overview");
  } catch (err) { toast(err.message, true); }
};
$("#hist-table").onclick = async (e) => {
  const b = e.target.closest(".del"); if (!b) return;
  try { await api(`/api/sets/${b.dataset.id}`, { method: "DELETE" }); toast("Deleted"); b.closest("tr").remove(); invalidate("overview"); }
  catch (err) { toast(err.message, true); }
};
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

// ---------- boot ----------
const first = location.hash.slice(1);
if (first && $(`#view-${first}`)) { $(".view.active").classList.remove("active"); $(`#view-${first}`).classList.add("active"); $$(".nav").forEach((b) => b.classList.toggle("active", b.dataset.view === first)); S.view = first; }
requestAnimationFrame(() => $(".view.active").classList.add("in"));
load(S.view);
