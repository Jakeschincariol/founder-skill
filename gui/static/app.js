/* Founder GUI: the page. Plain JS, no build step.
   Reads the hub's JSON API, re-renders the open view when files change (SSE),
   and in an exported file reads the frozen snapshot instead. */
(function () {
  "use strict";
  const SNAP = window.__FOUNDER_SNAPSHOT__ || null;
  const esc = MD.esc, t = I18N.t;
  const $ = (s, el) => (el || document).querySelector(s);
  const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));

  const STEP_TAB = { board: "board", competitors: "competitors", consumer: "panel", pricing: "pricing", offer: "offer", cfo: "cfo" };
  const TABS = ["pipeline", "board", "competitors", "panel", "pricing", "offer", "cfo", "docs", "feedback", "rounds", "runs"];
  const TAB_STEPS = { board: ["board"], competitors: ["competitors"], panel: ["consumer"], pricing: ["pricing", "consumer"], offer: ["offer", "consumer"], cfo: ["cfo"] };
  const S = { projects: [], pid: null, tab: "pipeline", sub: null, query: {}, st: null, ui: {}, run: null };

  // ── helpers ──────────────────────────────────────────────────────────────────
  async function api(url, opts) {
    opts = opts || {};
    if (SNAP) {
      if (opts.method && opts.method !== "GET") throw new Error(t("Read-only export"));
      const key = decodeURIComponent(url.replace(/[?&]round=[^&]*/, ""));
      if (key in SNAP.data) return JSON.parse(JSON.stringify(SNAP.data[key]));
      throw new Error(t("Not included in this export"));
    }
    const r = await fetch(url, { method: opts.method || "GET", headers: { "Content-Type": "application/json", "X-Founder-GUI": "1" },
      body: opts.body ? JSON.stringify(opts.body) : undefined });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { const e = new Error(j.error || r.statusText); e.status = r.status; e.data = j; throw e; }
    return j;
  }
  const P = (view, extra) => {
    const q = new URLSearchParams(extra || {});
    if (S.query.round) q.set("round", S.query.round);
    const s = q.toString();
    return "/api/p/" + S.pid + "/" + view + (s ? "?" + s : "");
  };
  const fileUrl = path => P("file", { path });
  const LOC = () => (I18N.lang === "pt" ? "pt-BR" : "en-US");  // numbers follow the UI language, not the browser
  const money = (v, d) => v == null ? "n/a" : (v < 0 ? "-$" : "$") + Math.abs(v).toLocaleString(LOC(), { minimumFractionDigits: d == null ? 0 : d, maximumFractionDigits: d == null ? 0 : d });
  const money2 = v => money(v, 2);
  const pct = (v, d) => v == null ? "n/a" : (v * 100).toFixed(d || 0) + "%";
  const intf = v => v == null ? "n/a" : (isFinite(v) ? Math.ceil(v).toLocaleString(LOC()) : "never");
  function ago(ts) {
    if (!ts) return "";
    const s = Date.now() / 1000 - ts;
    if (s < 60) return t("just now");
    if (s < 3600) return t("{n} min ago", { n: Math.floor(s / 60) });
    if (s < 86400) return t("{n} h ago", { n: Math.floor(s / 3600) });
    return new Date(ts * 1000).toLocaleDateString(LOC());
  }
  function toast(msg) {
    const el = $("#toast"); el.textContent = msg; el.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(() => { el.hidden = true; }, 3200);
  }
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }
  const chip = (cls, text) => '<span class="chip ' + esc(cls) + '">' + esc(text) + "</span>";
  const stepName = k => t("step." + k);
  const empty = msg => '<div class="empty">' + msg + "</div>";
  const cmd = k => "/founder-skill:founder-" + k;

  // ── routing ──────────────────────────────────────────────────────────────────
  function parseHash() {
    const h = location.hash.replace(/^#\/?/, "");
    const [path, qs] = h.split("?");
    const parts = path.split("/").filter(Boolean);
    S.query = Object.fromEntries(new URLSearchParams(qs || ""));
    if (parts[0] === "p" && parts[1]) {
      S.pid = parts[1]; S.tab = TABS.includes(parts[2]) ? parts[2] : "pipeline"; S.sub = parts.slice(3).join("/") || null;
    } else if (SNAP) {
      S.pid = SNAP.project; S.tab = "pipeline"; S.sub = null;
    } else { S.pid = null; }
  }
  function go(tab, sub, query) {
    const q = new URLSearchParams(query || (S.query.round ? { round: S.query.round } : {})).toString();
    location.hash = "#/p/" + S.pid + "/" + tab + (sub ? "/" + sub : "") + (q ? "?" + q : "");
  }

  // ── sidebar ──────────────────────────────────────────────────────────────────
  async function loadProjects() {
    try { S.projects = await api("/api/projects"); } catch (e) { S.projects = []; }
    renderProjects();
  }
  function renderProjects() {
    $("#projects").innerHTML = S.projects.map(p => {
      return '<a class="proj' + (p.id === S.pid ? " on" : "") + '" href="#/p/' + p.id + '/pipeline" title="' + esc(p.root) + '">' +
        '<div class="t"><span>' + esc(p.name) + "</span>" + (p.running.length ? chip("running", t("live")) : "") + "</div>" +
        '<div class="meta" style="margin-top:2px"><span class="num" style="font-size:11px">' + esc(p.root.split("/").pop()) + "/</span></div>" +
        '<div class="meta"><span class="verdict ' + esc(p.verdict.replace(" ", "-")) + '" style="padding:0 6px;font-size:10.5px">' + esc(t(p.verdict)) + "</span>" +
        "<span>" + p.done + "/" + p.total + "</span>" + (p.sessions > 1 ? '<span class="chip warn" title="' + esc(t("Claude sessions in this folder")) + '">⚠ ' + p.sessions + "</span>" : "") +
        "<span>" + esc(ago(p.updated)) + "</span></div></a>";
    }).join("") || '<div class="muted" style="padding:6px">' + esc(t("No projects yet")) + "</div>";
    $("#hub-note").textContent = SNAP ? t("Exported report") : t("{n} projects", { n: S.projects.length });
  }

  // ── main frame ───────────────────────────────────────────────────────────────
  async function render() {
    parseHash();
    renderProjects();
    const main = $("#main");
    if (!S.pid) { main.innerHTML = welcome(); return; }
    try {
      S.st = await api(P("state"));
    } catch (e) {
      main.innerHTML = '<div class="empty-state"><h1>' + esc(t("Project not found")) + "</h1><p>" + esc(e.message) + "</p></div>";
      return;
    }
    main.innerHTML = '<div id="hdr">' + header() + '</div><div id="view"></div>';
    bindHeader();
    await renderView();
  }

  function welcome() {
    return '<div class="empty-state"><h1>Founder GUI</h1><p>' + esc(t("Follow the founder skills in the browser: every step, suggestion and result, live while Claude works.")) +
      "</p><p>" + esc(t("Open a project from Claude Code:")) + "</p><pre>/founder-skill:founder-gui</pre><p>" + esc(t("or from a terminal:")) +
      "</p><pre>python3 gui/serve.py --dir path/to/project\npython3 gui/demo.py /tmp/moss-demo   # " + esc(t("a demo project")) + "</pre></div>";
  }

  function header() {
    const st = S.st, v = st.verdict.verdict;
    const running = st.steps.filter(s => s.status === "running").map(s => s.key);
    let h = '<div class="head"><div><h1>' + esc(st.name) + '</h1><div class="path">' + esc(st.root) + "</div></div>" +
      '<div class="actions"><span class="verdict ' + esc(v.replace(" ", "-")) + '">' + esc(t(v)) + "</span>";
    if (SNAP) h += '<span class="snapshot-note">' + esc(t("Exported {d}, read-only", { d: new Date(SNAP.exported * 1000).toLocaleString(LOC()) })) + "</span>";
    else h += '<a class="btn" href="/api/p/' + S.pid + '/export">⤓ ' + esc(t("Export HTML")) + "</a>" +
      '<button class="btn" id="snap-btn">◷ ' + esc(t("Save round")) + "</button>" +
      '<button class="btn danger sm" id="forget">' + esc(t("Forget")) + "</button>";
    h += "</div></div>";
    if (S.query.round) h += '<div class="banner info" style="margin-top:14px"><span>' + esc(t("Viewing round {r} (read-only copy).", { r: S.query.round })) +
      '</span><a class="btn sm" href="#/p/' + S.pid + "/" + S.tab + '">' + esc(t("Back to current")) + "</a></div>";
    if (st.sessions && st.sessions.length > 1) h += '<div class="banner warn" style="margin-top:14px"><span>⚠ ' +
      esc(t("{n} Claude sessions are open in this folder. The skills do not lock files: two sessions running the same step overwrite each other.", { n: st.sessions.length })) +
      "</span><small>PIDs " + st.sessions.map(s => s.pid).join(", ") + "</small></div>";
    if (st.gui_run) h += '<div class="banner run" style="margin-top:14px"><span>' + chip("running", t("running")) + " " +
      esc(t("{s} is running from the GUI.", { s: stepName(st.gui_run.step) })) + '</span><a class="btn sm" href="#/p/' + S.pid + "/runs/" + esc(st.gui_run.run) + '">' + esc(t("Follow")) + "</a></div>";
    const tabStep = tab => (TAB_STEPS[tab] || []).some(k => running.includes(k));
    h += '<nav class="tabs">' + TABS.filter(x => !(SNAP && (x === "runs" || x === "rounds"))).map(x =>
      '<a href="#/p/' + S.pid + "/" + x + (S.query.round ? "?round=" + encodeURIComponent(S.query.round) : "") + '" class="' + (x === S.tab ? "on" : "") + '">' + esc(t("tab." + x)) +
      (tabStep(x) ? '<span class="dot"></span>' : "") + (x === "feedback" && openFeedback() ? ' <span class="chip">' + openFeedback() + "</span>" : "") + "</a>").join("") + "</nav>";
    return h;
  }
  const openFeedback = () => Object.values(S.st.feedback || {}).reduce((a, f) => a + f.open, 0);

  function bindHeader() {
    const sb = $("#snap-btn");
    if (sb) sb.onclick = async () => {
      const label = (S.ui.roundLabel || "").trim() || t("Round") + " " + new Date().toLocaleString(LOC());
      try { await api("/api/p/" + S.pid + "/rounds", { method: "POST", body: { label } }); toast(t("Round saved")); if (S.tab === "rounds") renderView(); }
      catch (e) { toast(e.message); }
    };
    const fg = $("#forget");
    if (fg) fg.onclick = async () => {
      if (!fg.dataset.armed) { fg.dataset.armed = "1"; fg.textContent = t("Click again to forget (files stay)"); return; }
      await api("/api/projects/" + S.pid, { method: "DELETE" });
      location.hash = "#/"; loadProjects();
    };
  }

  async function renderView() {
    const el = $("#view");
    if (!el) return;
    try { await (VIEWS[S.tab] || VIEWS.pipeline)(el); }
    catch (e) { el.innerHTML = empty(esc(e.message)); console.error(e); }
  }

  // ── pipeline ─────────────────────────────────────────────────────────────────
  const VIEWS = {};
  VIEWS.pipeline = async el => {
    const st = S.st;
    const checks = st.verdict.checks.map(c => '<li><span class="ic ' + (c.ok ? "ok" : "ko") + '">' + (c.ok ? "✓" : "✗") + "</span><span>" + esc(c.text) + "</span></li>").join("");
    const next = st.next;
    let h = '<div class="grid g-side">';
    h += '<div class="card"><div class="card-head"><h2>' + esc(t("Verdict")) + '</h2><span class="verdict ' + esc(st.verdict.verdict.replace(" ", "-")) + '">' + esc(t(st.verdict.verdict)) + "</span></div>" +
      (checks ? '<ul class="checks">' + checks + "</ul>" : '<p class="muted">' + esc(t("No numbers yet. The verdict is computed once the CFO has run.")) + "</p>") +
      (next ? '<div class="banner info" style="margin:14px 0 0"><span>' + esc(t("Next step:")) + " <b>" + esc(stepName(next)) + "</b> <code class=\"copy\" data-copy=\"" + esc(cmd(next)) + '">' + esc(cmd(next)) + "</code></span>" +
        (SNAP ? "" : '<a class="btn sm primary" href="#/p/' + S.pid + "/runs?step=" + next + '">▶ ' + esc(t("Run from here")) + "</a>") + "</div>" : "") + "</div>";
    h += '<div class="card"><h2>' + esc(t("Board conditions")) + "</h2>" + checklist(st.checklist) + "</div></div>";
    h += '<h2 style="margin:22px 0 10px">' + esc(t("The eleven steps")) + '</h2><div class="pipe">';
    for (const s of st.steps) {
      const fb = (st.feedback || {})[s.key];
      const open = STEP_TAB[s.key] ? "#/p/" + S.pid + "/" + STEP_TAB[s.key] : "#/p/" + S.pid + "/docs/" + encodeURIComponent(s.primary);
      h += '<div class="step ' + s.status + (s.key === next ? " next" : "") + '"><h3>' + esc(stepName(s.key)) + '</h3><div class="role">' + esc(t("role." + s.key)) + "</div>" +
        '<div class="row">' + chip(s.status, t("status." + s.status)) + (s.updated ? "<small>" + esc(ago(s.updated)) + "</small>" : "") +
        (fb && fb.open ? chip("warn", "💬 " + fb.open) : "") + "</div>" +
        (s.stale_by.length ? '<div class="row"><small>' + esc(t("changed since: {f}", { f: s.stale_by.join(", ") })) + "</small></div>" : "") +
        '<div class="acts">' + (s.files.length ? '<a class="btn sm" href="' + open + '">' + esc(t("Open")) + "</a>" : "") +
        (SNAP ? "" : '<a class="btn sm" href="#/p/' + S.pid + "/runs?step=" + s.key + '">▶ ' + esc(t("Run")) + "</a>") +
        '<button class="btn sm copy" data-copy="' + esc(cmd(s.key)) + '" title="' + esc(t("Copy the command")) + '">⧉</button></div></div>';
    }
    h += "</div>";
    el.innerHTML = h;
    bindChecklist(el);
  };

  function checklist(items) {
    if (!items || !items.length) return '<p class="muted">' + esc(t("The board's conditions show up here once board.md has a checklist.")) + "</p>";
    const done = items.filter(i => i.done).length;
    return '<div class="progress" style="margin-bottom:10px"><i style="width:' + (100 * done / items.length) + '%;background:var(--accent)"></i></div><div class="checklist">' +
      items.map(i => '<label><input type="checkbox" data-tick="' + i.id + '"' + (i.done ? " checked" : "") + (SNAP || S.query.round ? " disabled" : "") + '><span class="' + (i.done ? "done" : "") + '">' + MD.inline(i.text) + "</span></label>").join("") + "</div>";
  }
  function bindChecklist(el) {
    $$("[data-tick]", el).forEach(cb => cb.onchange = async () => {
      try { S.st.checklist = await api("/api/p/" + S.pid + "/checklist", { method: "POST", body: { id: cb.dataset.tick, done: cb.checked } }); renderView(); }
      catch (e) { toast(e.message); }
    });
  }

  // ── commentable markdown (phase 3) ───────────────────────────────────────────
  function doc(text, file, step) {
    if (!text) return "";
    const can = step && step !== "feedback" && !SNAP && !S.query.round;
    return '<div class="md' + (can ? " commentable" : "") + '" data-file="' + esc(file || "") + '" data-step="' + esc(step || "") + '">' + MD.render(text, { commentable: can }) + "</div>";
  }
  document.addEventListener("click", async ev => {
    const cp = ev.target.closest("[data-copy]");
    if (cp) { try { await navigator.clipboard.writeText(cp.dataset.copy); toast(t("Copied: {c}", { c: cp.dataset.copy })); } catch (e) { toast(cp.dataset.copy); } return; }
    const b = ev.target.closest("[data-comment]");
    if (!b) return;
    const blk = b.closest(".blk"), box = b.closest(".md");
    if (blk.nextElementSibling && blk.nextElementSibling.classList.contains("cform")) { blk.nextElementSibling.remove(); return; }
    const form = document.createElement("form");
    form.className = "cform";
    form.innerHTML = '<div class="quote">' + esc(blk.dataset.src) + '</div><div class="kinds">' +
      ["change", "keep", "question"].map((k, i) => '<label><input type="radio" name="kind" value="' + k + '"' + (i ? "" : " checked") + "> " + esc(t("kind." + k)) + "</label>").join("") +
      '</div><textarea name="text" placeholder="' + esc(t("What should the skill do with this?")) + '"></textarea><div style="display:flex;gap:8px;justify-content:flex-end">' +
      '<button type="button" class="btn sm" data-cancel>' + esc(t("Cancel")) + '</button><button class="btn sm primary">' + esc(t("Save feedback")) + "</button></div>";
    blk.after(form);
    $("textarea", form).focus();
    $("[data-cancel]", form).onclick = () => form.remove();
    form.onsubmit = async e => {
      e.preventDefault();
      const fd = new FormData(form), quote = blk.dataset.src.replace(/\s+/g, " ").slice(0, 90);
      const text = fd.get("text").trim() + (quote ? ' [re: "' + quote.replace(/[()]/g, "") + '"]' : "");
      const ref = box.dataset.file + (blk.dataset.section ? " § " + blk.dataset.section.replace(/[()]/g, "") : "");
      try {
        await api("/api/p/" + S.pid + "/feedback/" + box.dataset.step, { method: "POST", body: { kind: fd.get("kind"), text, ref } });
        form.outerHTML = '<div class="banner info">' + esc(t("Saved to founder/feedback/{s}.md. The skill reads it on its next run.", { s: box.dataset.step })) + "</div>";
      } catch (err) { toast(err.message); }
    };
  });

  // ── board ────────────────────────────────────────────────────────────────────
  VIEWS.board = async el => {
    const b = await api(P("board"));
    if (!b.memos.length && !b.summary && !b.idea) { el.innerHTML = empty(esc(t("No board yet. Run {c}.", { c: cmd("board") }))); return; }
    const scores = b.memos.map(m => m.score).filter(x => x != null);
    const avg = scores.length ? (scores.reduce((a, x) => a + x, 0) / scores.length).toFixed(1) : "n/a";
    let h = '<div class="grid g4" style="margin-bottom:14px">' +
      kpi(avg, t("average score")) + b.memos.map(m => kpi(m.vote || "?", t("lens.title", { l: m.lens }))).join("") + "</div>";
    h += '<div class="grid g3">' + b.memos.map(m => {
      const secs = Object.entries(m.sections).map(([k, v]) => '<div class="sec"><h4>' + esc(k) + "</h4>" + doc(v, m.file, "board") + "</div>").join("");
      return '<div class="card memo"><div class="top"><div><h2>' + esc(t("lens.title", { l: m.lens })) + "</h2>" + (m.vote ? chip(m.vote.replace(" ", "-"), m.vote) : "") + "</div>" +
        (m.score != null ? '<div class="score" style="--s:' + m.score + '"><span>' + m.score + "</span></div>" : "") + "</div>" + secs + "</div>";
    }).join("") + "</div>";
    h += '<div class="grid g-side" style="margin-top:14px"><div class="card"><h2>' + esc(t("The chair's summary")) + "</h2>" + (doc(b.summary, "board.md", "board") || '<p class="muted">board.md</p>') + "</div>" +
      '<div class="card"><h2>' + esc(t("Board conditions")) + "</h2>" + checklist(b.checklist) + "<h2 style=\"margin-top:18px\">" + esc(t("The idea")) + "</h2>" + doc(b.idea, "idea.md", "board") + "</div></div>";
    el.innerHTML = h;
    bindChecklist(el);
  };
  const kpi = (v, l, d) => '<div class="card kpi"><div class="v">' + esc(v) + '</div><div class="l">' + esc(l) + "</div>" + (d ? '<div class="d">' + d + "</div>" : "") + "</div>";

  // ── competitors ──────────────────────────────────────────────────────────────
  VIEWS.competitors = async el => {
    const c = await api(P("competitors"));
    let ours = null;
    try { ours = (await api(P("cfo"))).spec; } catch (e) { /* no numbers yet */ }
    if (!c.rows.length && !c.report) { el.innerHTML = empty(esc(t("No competitor map yet. Run {c}.", { c: cmd("competitors") }))); return; }
    const types = {};
    c.rows.forEach(r => { types[r.type] = (types[r.type] || 0) + 1; });
    let h = '<div class="grid g4" style="margin-bottom:14px">' + kpi(c.rows.length, t("competitors")) +
      Object.entries(types).slice(0, 3).map(([k, n]) => kpi(n, k)).join("") + "</div>";
    h += '<div class="grid g-side"><div class="card"><h2>' + esc(t("Price vs rating")) + '</h2><div id="sc"></div></div><div class="card"><h2>' + esc(t("The gap")) + "</h2>" + doc(c.report, "competitors.md", "competitors") + "</div></div>";
    h += '<div class="card" style="margin-top:14px"><h2>' + esc(t("Every competitor")) + '</h2><div class="table-wrap"><table class="t"><thead><tr><th>' +
      [t("name"), t("type"), t("where"), t("price"), t("rating"), t("reviews"), t("positioning")].map(esc).join("</th><th>") + "</th></tr></thead><tbody>" +
      c.rows.map(r => "<tr><td>" + (r.url ? '<a href="' + esc(r.url) + '" target="_blank" rel="noopener">' + esc(r.name) + "</a>" : esc(r.name)) + "</td><td>" + chip("", r.type || "") + "</td><td>" + esc(r.location_or_channel || "") +
        '</td><td class="r">' + esc(r.price_of_comparable_item || "") + '</td><td class="r">' + esc(r.rating || "") + '</td><td class="r">' + esc(r.review_count || "") + "</td><td>" + esc(r.positioning_line || "") + "</td></tr>").join("") +
      "</tbody></table></div></div>";
    el.innerHTML = h;
    Charts.scatter($("#sc"), { points: c.rows.map((r, i) => ({ x: r.price, y: r.rating_num, label: r.name, cls: { direct: "f3", indirect: "f2", substitute: "f4" }[r.type] || "f" + ((i % 5) + 1) })),
      xfmt: money2, yfmt: v => (+v).toFixed(1), xlabel: t("price of the comparable item"), ylabel: t("rating"),
      vline: ours && ours.price ? { x: ours.price, label: t("you {p}", { p: money2(ours.price) }) } : null });
  };

  // ── consumer panel ───────────────────────────────────────────────────────────
  VIEWS.panel = async el => {
    const p = await api(P("panel"));
    if (!p.exists) { el.innerHTML = empty(esc(t("No panel yet. Run {c}.", { c: cmd("consumer") }))); return; }
    const ui = S.ui.panel = S.ui.panel || { seg: "", beh: "", buy: "" };
    const seen = S.ui.panelSeen || {};
    const res = p.live || p.results;
    const buyers = p.buyers;
    const segs = [...new Set(buyers.map(b => b.segment))], behs = [...new Set(buyers.map(b => b.behaviour))];
    const match = b => (!ui.seg || b.segment === ui.seg) && (!ui.beh || b.behaviour === ui.beh) &&
      (!ui.buy || (ui.buy === "yes" ? b.answer && b.answer.buys : ui.buy === "no" ? b.answer && !b.answer.buys : !b.answer));
    const live = p.answered < p.n;
    let h = '<div class="grid g4" style="margin-bottom:14px">' +
      kpi(res ? pct(res.buy_rate) : "n/a", t("would buy")) + kpi(res ? res.buys + " · " + res.passes : "n/a", t("buy · pass")) +
      kpi(p.answered + "/" + p.n, t("answered"), live ? '<div class="progress" style="margin-top:6px"><i style="width:' + (100 * p.answered / p.n) + '%"></i></div>' : "") +
      kpi(res && res.purchases_first_month_per_buyer != null ? res.purchases_first_month_per_buyer.toFixed(1) : "n/a", t("purchases in month 1, per buyer")) + "</div>";
    h += '<div class="grid g-side"><div class="card"><div class="card-head"><h2>' + esc(t("The buyers")) + "</h2>" + (live ? chip("running", t("answers arriving")) : "") + "</div>" +
      '<div class="filters">' + sel("seg", t("every segment"), segs, ui.seg) + sel("beh", t("every behaviour"), behs, ui.beh) +
      sel("buy", t("everyone"), [["yes", t("buys")], ["no", t("passes")], ["wait", t("no answer yet")]], ui.buy) +
      '<span class="legend"><span><i style="background:var(--good)"></i>' + esc(t("buys")) + '</span><span><i style="background:color-mix(in srgb,var(--bad) 60%,var(--panel))"></i>' + esc(t("passes")) +
      '</span><span><i style="background:var(--muted-soft)"></i>' + esc(t("waiting")) + "</span></span></div>" +
      '<div class="tiles">' + buyers.map(b => {
        const cls = b.answer ? (b.answer.buys ? "yes" : "no") : "";
        const fresh = b.answer && seen[b.id] === false ? " fresh" : "";
        return '<button class="tile ' + cls + (match(b) ? "" : " dim") + fresh + '" data-buyer="' + b.id + '" title="' + esc(b.name + ", " + b.age + " · " + b.segment + " · " + b.behaviour) + '">' + b.id.slice(1) + "</button>";
      }).join("") + "</div></div>";
    h += '<div class="card"><h2>' + esc(t("The pitch they saw")) + '</h2><div class="md"><p>' + MD.inline(p.pitch || "").replace(/\n/g, "<br>") + "</p></div>" +
      (p.pitch_now && p.pitch && p.pitch_now.trim() !== p.pitch.trim() ? '<div class="banner warn">' + esc(t("pitch.md changed after this panel was dealt. Re-run the panel to test the new pitch.")) + "</div>" : "") +
      '<p class="muted" style="font-size:12px">' + esc(t("Seed {s}: the same cards can be dealt again.", { s: p.seed })) + "</p></div></div>";
    if (res) {
      const barsFor = (rows) => '<div class="bars">' + rows.map(([k, n, r]) => '<div class="bar"><span class="lbl" title="' + esc(k) + '">' + esc(k) + ' <small>(' + n + ')</small></span><span class="track"><i style="width:' + (r * 100) + '%"></i></span><span class="n">' + pct(r) + "</span></div>").join("") + "</div>";
      h += '<div class="grid g3" style="margin-top:14px"><div class="card"><h3>' + esc(t("By segment")) + "</h3>" + barsFor(res.by_segment) + '</div><div class="card"><h3>' + esc(t("By behaviour")) + "</h3>" + barsFor(res.by_behaviour) +
        '</div><div class="card"><h3>' + esc(t("By income")) + "</h3>" + barsFor(res.by_income) + "</div></div>";
      const reasons = (rows, total) => '<div class="reasons">' + rows.map(([code, n, quotes]) => '<div class="reason"><div class="bar"><span class="lbl"><b>' + esc(code) + '</b></span><span class="track"><i style="width:' + (100 * n / Math.max(1, total)) + '%;background:var(--c3)"></i></span><span class="n">' + n + "</span></div>" +
        quotes.map(q => '<div class="q">"' + esc(q) + '"</div>').join("") + "</div>").join("") + "</div>";
      const flips = {};
      (res.flip || []).forEach(f => { const k = f.trim().replace(/\.$/, ""); flips[k] = (flips[k] || 0) + 1; });
      h += '<div class="grid g3" style="margin-top:14px"><div class="card"><h3>' + esc(t("Why they pass")) + "</h3>" + reasons(res.why_not, res.passes) + '</div><div class="card"><h3>' + esc(t("Why they buy")) + "</h3>" + reasons(res.why_yes, res.buys) +
        '</div><div class="card"><h3>' + esc(t("What would flip a no")) + '</h3><div class="bars">' + Object.entries(flips).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([k, n]) =>
          '<div class="bar"><span class="lbl" title="' + esc(k) + '">' + esc(k) + '</span><span class="track"><i style="width:' + (100 * n / Math.max(1, res.passes)) + '%;background:var(--c2)"></i></span><span class="n">' + n + "</span></div>").join("") + "</div>" +
        (SNAP ? "" : '<p style="margin-top:12px"><a class="btn sm" href="#/p/' + S.pid + '/feedback?step=offer">' + esc(t("Turn these into feedback for the offer")) + "</a></p>") + "</div></div>";
    }
    if (p.report) h += '<details class="card" style="margin-top:14px"><summary class="link" style="font-size:14px">panel/results.md</summary>' + doc(p.report, "panel/results.md", "consumer") + "</details>";
    el.innerHTML = h;
    S.ui.panelSeen = Object.fromEntries(buyers.map(b => [b.id, !!b.answer]));
    $$("select[data-f]", el).forEach(s => s.onchange = () => { ui[s.dataset.f] = s.value; VIEWS.panel(el); });
    $$("[data-buyer]", el).forEach(b => b.onclick = () => buyer(buyers.find(x => x.id === b.dataset.buyer)));
  };
  function sel(key, all, opts, cur) {
    return '<select data-f="' + key + '"><option value="">' + esc(all) + "</option>" + opts.map(o => {
      const [v, l] = Array.isArray(o) ? o : [o, o];
      return '<option value="' + esc(v) + '"' + (v === cur ? " selected" : "") + ">" + esc(l) + "</option>";
    }).join("") + "</select>";
  }
  async function buyer(b) {
    const a = b.answer;
    let h = '<div class="card-head"><h2>' + esc(b.name) + ", " + b.age + ' <small class="num">' + b.id + '</small></h2><button class="btn sm" data-close>✕</button></div><div class="persona"><dl>' +
      [["segment", b.segment], ["income", money(b.income)], ["behaviour", b.behaviour + (b.behaviour_how ? ": " + b.behaviour_how : "")], ["habit", b.habit], ["first objection", b.objection]]
        .filter(x => x[1]).map(([k, v]) => "<dt>" + esc(t(k)) + "</dt><dd>" + esc(v) + "</dd>").join("") + "</dl></div>";
    if (a) {
      h += '<div class="card" style="margin-top:14px"><div class="card-head"><h3>' + esc(t("The answer")) + "</h3>" + chip(a.buys ? "good" : "bad", a.buys ? t("buys") : t("passes")) + "</div>" +
        '<p style="font-size:15px;font-family:var(--serif)">"' + esc(a.reason) + '"</p><div class="persona"><dl>' +
        [["reason", a.reason_code], ["objection", a.objection], ["would change my mind", a.would_change_my_mind], ["purchases in month 1", a.purchases_first_month]]
          .filter(x => x[1] !== "" && x[1] != null).map(([k, v]) => "<dt>" + esc(t(k)) + "</dt><dd>" + esc(v) + "</dd>").join("") + "</dl></div>" +
        '<h3 style="margin-top:14px">' + esc(t("Price answers")) + '</h3><table class="t"><tr><th>' + esc(t("too cheap")) + '</th><th>' + esc(t("a bargain")) + "</th><th>" + esc(t("getting expensive")) + "</th><th>" + esc(t("too expensive")) + '</th></tr><tr><td class="r">' +
        [a.price_too_cheap, a.price_cheap, a.price_expensive, a.price_too_expensive].map(money2).join('</td><td class="r">') + "</td></tr></table></div>";
    } else h += '<div class="empty" style="margin-top:14px">' + esc(t("No answer yet.")) + "</div>";
    h += '<details style="margin-top:14px"><summary class="link">' + esc(t("The brief this buyer agent received")) + '</summary><pre id="brief" class="md" style="white-space:pre-wrap;font-size:12px">…</pre></details>';
    openDrawer(h);
    try { $("#brief").textContent = (await api(P("panel/brief/" + b.id))).text; } catch (e) { $("#brief").textContent = t("Not available"); }
  }
  function openDrawer(html) {
    const d = $("#drawer");
    $(".drawer-body", d).innerHTML = html; d.hidden = false;
    d.onclick = e => { if (e.target === d || e.target.closest("[data-close]")) d.hidden = true; };
  }
  document.addEventListener("keydown", e => { if (e.key === "Escape") $("#drawer").hidden = true; });

  // ── pricing ──────────────────────────────────────────────────────────────────
  VIEWS.pricing = async el => {
    const p = await api(P("pricing"));
    if (!p.analysis && !p.report) { el.innerHTML = empty(esc(t("No price answers yet: the consumer panel collects them. Then run {c}.", { c: cmd("pricing") }))); return; }
    let h = "";
    if (p.analysis) {
      const pts = p.analysis.points;
      h += '<div class="grid g4" style="margin-bottom:14px">' + kpi(t("{a} to {b}", { a: money2(pts.PMC), b: money2(pts.PME) }), t("acceptable range")) + kpi(money2(pts.OPP), t("optimal price (OPP)")) +
        kpi(money2(pts.IPP), t("indifference price (IPP)")) + kpi(p.price != null ? money2(p.price) : "n/a", t("your price now"),
          p.price != null && pts.PMC != null ? (p.price >= pts.PMC && p.price <= pts.PME ? '<span class="up">' + esc(t("inside the range")) + "</span>" : '<span class="down">' + esc(t("outside the range")) + "</span>") : "") + "</div>";
      h += '<div class="card"><div class="card-head"><h2>' + esc(t("Price sensitivity (Van Westendorp)")) + '</h2><small>' + esc(t("{n} complete answers, {d} dropped", { n: p.n, d: p.dropped })) + '</small></div><div id="vw"></div>' +
        '<p class="muted" style="font-size:12px">' + esc(t("Shaded: the acceptable range. Dots: competitor prices. Simulated buyers: use the range to pick what to test.")) + "</p></div>";
    }
    h += '<div class="grid g2" style="margin-top:14px"><div class="card"><h2>pricing.md</h2>' + (doc(p.report, "pricing.md", "pricing") || '<p class="muted">' + esc(t("Not written yet.")) + "</p>") + '</div><div class="card"><h2>pricing-curve.md</h2>' + (doc(p.curve_report, "pricing-curve.md", "pricing") || "") + "</div></div>";
    el.innerHTML = h;
    if (p.analysis) {
      const c = p.curves, pts = p.analysis.points;
      const markers = [{ x: pts.PMC, label: "PMC" }, { x: pts.OPP, label: "OPP" }, { x: pts.IPP, label: "IPP" }, { x: pts.PME, label: "PME" }];
      if (p.price != null) markers.push({ x: p.price, label: t("you"), cls: "price" });
      if (p.variable_per_unit != null) markers.push({ x: p.variable_per_unit, label: t("unit cost") });
      Charts.line($("#vw"), { x: c.grid, label: "Van Westendorp", height: 320, band: p.analysis.range, markers, ymin: 0, ymax: 1,
        dots: p.competitors.map(x => ({ x: x.price, label: x.name + " " + money2(x.price) })),
        series: [{ name: t("too cheap"), values: c.too_cheap }, { name: t("a bargain"), values: c.cheap }, { name: t("too expensive"), values: c.too_expensive }, { name: t("getting expensive"), values: c.expensive }],
        xfmt: money2, yfmt: v => pct(v) });
    }
  };

  // ── offer ────────────────────────────────────────────────────────────────────
  VIEWS.offer = async el => {
    const o = await api(P("offer"));
    let panel = null;
    try { panel = await api(P("panel")); } catch (e) { /* none */ }
    if (!o.report && !o.pitch_v1) { el.innerHTML = empty(esc(t("No offer yet. Run {c} after the panel.", { c: cmd("offer") }))); return; }
    let h = "";
    if (o.pitch_v1 || o.pitch_now) {
      h += '<div class="card"><div class="card-head"><h2>' + esc(t("The pitch, before and after")) + "</h2>" +
        (panel && (panel.live || panel.results) ? chip("", t("panel now: {r} buy", { r: pct((panel.live || panel.results).buy_rate) })) : "") + "</div>" +
        '<div class="side-by-side"><div><h3>pitch-v1.md</h3><pre>' + wordDiff(o.pitch_v1 || "", o.pitch_now || "", "del") + "</pre></div><div><h3>pitch.md</h3><pre>" + wordDiff(o.pitch_v1 || "", o.pitch_now || "", "ins") + "</pre></div></div>" +
        '<p class="muted" style="font-size:12px">' + esc(t("To compare buy rates before and after, save a round before the offer re-test, then compare rounds.")) + "</p></div>";
    }
    h += '<div class="card" style="margin-top:14px"><h2>offer.md</h2>' + doc(o.report, "offer.md", "offer") + "</div>";
    el.innerHTML = h;
  };
  function wordDiff(a, b, side) {
    const A = a.split(/(\s+)/), B = b.split(/(\s+)/);
    const n = A.length, m = B.length;
    if (n * m > 4e6) return esc(side === "del" ? a : b);
    const L = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
    for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = A[i] === B[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
    let i = 0, j = 0, out = "";
    while (i < n || j < m) {
      if (i < n && j < m && A[i] === B[j]) { out += esc(A[i]); i++; j++; }
      else if (j < m && (i >= n || L[i][j + 1] >= L[i + 1][j])) { if (side === "ins") out += /^\s+$/.test(B[j]) ? esc(B[j]) : '<mark class="ins">' + esc(B[j]) + "</mark>"; j++; }
      else { if (side === "del") out += /^\s+$/.test(A[i]) ? esc(A[i]) : '<mark class="del">' + esc(A[i]) + "</mark>"; i++; }
    }
    return out;
  }

  // ── cfo ──────────────────────────────────────────────────────────────────────
  VIEWS.cfo = async el => {
    const c = await api(P("cfo"));
    if (!c.spec) { el.innerHTML = empty(esc(t("No numbers yet. Run {c}.", { c: cmd("cfo") }))); return; }
    if (c.error) { el.innerHTML = '<div class="banner warn">' + esc(t("numbers.json has a problem: {e}", { e: c.error })) + "</div>"; return; }
    const a = c.analysis, u = a.unit;
    const ui = S.ui.cfo = S.ui.cfo || { price: a.price, volume: 100, variable: 100, fixed: 100, startup: 100 };
    let h = '<div class="grid g4" style="margin-bottom:14px">' +
      kpi(money2(a.contribution), t("each {u} earns, before fixed costs", { u }), pct(a.contribution_pct) + " " + esc(t("contribution"))) +
      kpi(intf(a.breakeven_per_day), t("{u}s a day to break even", { u }), a.capacity_per_day ? esc(t("capacity {c}", { c: a.capacity_per_day })) : "") +
      kpi(pct(a.margin_at_plan), t("profit margin at plan ({n}/day)", { n: a.plan_per_day })) +
      kpi(money(a.year1_profit), t("year 1 operating profit"), esc(t("after startup: {v}", { v: money(a.year1_after_startup) }))) + "</div>";
    h += '<div class="grid g4" style="margin-bottom:14px">' + kpi(money(a.startup), t("startup spend")) + kpi(money(a.cash_needed), t("cash needed before it pays for itself")) +
      kpi(a.payback_month ? t("month {m}", { m: a.payback_month }) : t("not in year 1"), t("startup money earned back")) + kpi(money(a.fixed_monthly), t("fixed costs a month")) + "</div>";
    h += '<div class="grid g-side"><div class="card"><div class="card-head"><h2>' + esc(t("Year 1, month by month")) + '</h2><small id="wi-note"></small></div><div id="y1"></div></div>';
    h += '<div class="card"><div class="card-head"><h2>' + esc(t("What if")) + "</h2>" + (SNAP ? "" : '<button class="btn sm" id="wi-reset">' + esc(t("Reset")) + "</button>") + "</div>" +
      (SNAP ? '<p class="muted">' + esc(t("The what-if needs the live GUI.")) + "</p>" : '<div class="sliders">' +
        slider("price", t("price per {u}", { u }), +(a.price * 0.5).toFixed(2), +(a.price * 1.6).toFixed(2), 0.05, ui.price, money2) +
        slider("volume", t("sales volume"), 40, 160, 5, ui.volume, v => v + "%") +
        slider("variable", t("unit costs"), 50, 200, 5, ui.variable, v => v + "%") +
        slider("fixed", t("fixed costs"), 50, 200, 5, ui.fixed, v => v + "%") +
        slider("startup", t("startup spend"), 50, 200, 5, ui.startup, v => v + "%") + '</div><div id="wi-out" style="margin-top:14px"></div>') +
      '<p class="muted" style="font-size:12px">' + esc(t("Runs the CFO's own unit_economics.py on a copy. numbers.json is never changed.")) + "</p></div></div>";
    h += '<div class="card" style="margin-top:14px"><h2>' + esc(t("The three what-ifs every plan should survive")) + '</h2><div class="table-wrap"><table class="t"><thead><tr><th></th><th class="r">' +
      [t("price"), t("contribution"), t("margin at plan"), t("break-even/day"), t("year 1 profit"), t("cash needed"), t("payback")].map(esc).join('</th><th class="r">') + "</th></tr></thead><tbody>" +
      c.sensitivity.map(s => { const r = s.result; return "<tr><td>" + esc(s.label) + '</td><td class="r">' + [money2(r.price), money2(r.contribution), pct(r.margin_at_plan), intf(r.breakeven_per_day),
        '<span class="' + (r.year1_profit >= 0 ? "up" : "down") + '">' + money(r.year1_profit) + "</span>", money(r.cash_needed), r.payback_month ? t("month {m}", { m: r.payback_month }) : "n/a"].join('</td><td class="r">') + "</td></tr>"; }).join("") +
      "</tbody></table></div></div>";
    h += '<div class="grid g3" style="margin-top:14px">' + items(t("Cost of one {u}", { u }), a.variable_items) + items(t("Fixed, every month"), a.fixed_items) + items(t("Startup, once"), a.startup_items) + "</div>";
    h += '<div class="grid g2" style="margin-top:14px"><div class="card"><h2>cfo.md</h2>' + doc(c.report, "cfo.md", "cfo") + '</div><div class="card"><h2>cfo-sources.md</h2>' + (doc(c.sources, "cfo-sources.md", "cfo") || '<p class="muted">' + esc(t("Not written yet.")) + "</p>") + "</div></div>";
    el.innerHTML = h;
    const drawYear = (b, w) => Charts.bars($("#y1"), { labels: b.months.map(m => "M" + m.month), values: (w || b).months.map(m => m.profit), name: w ? t("profit (what-if)") : t("profit"),
      line: { name: t("cumulative, after startup"), values: (w || b).months.map(m => m.cumulative) }, ghost: w ? b.months.map(m => m.profit) : null, ghostName: t("profit (plan)"), yfmt: money, height: 280 });
    drawYear(a);
    if (SNAP) return;
    let timer;
    const recalc = async () => {
      const body = { price: ui.price, volume: ui.volume / 100, variable_scale: ui.variable / 100, fixed_scale: ui.fixed / 100, startup_scale: ui.startup / 100 };
      const same = Math.abs(ui.price - a.price) < 1e-9 && ui.volume === 100 && ui.variable === 100 && ui.fixed === 100 && ui.startup === 100;
      if (same) { drawYear(a); $("#wi-out").innerHTML = ""; $("#wi-note").textContent = ""; return; }
      try {
        const w = await api("/api/p/" + S.pid + "/cfo/whatif", { method: "POST", body });
        drawYear(a, w);
        $("#wi-note").textContent = t("showing the what-if; grey bars are the plan");
        const d = (x, y, f, good) => { const diff = x - y; return f(x) + ' <small class="' + ((good ? diff >= 0 : diff <= 0) ? "up" : "down") + '">' + (diff >= 0 ? "+" : "") + f(diff) + "</small>"; };
        $("#wi-out").innerHTML = '<table class="t"><tr><td>' + esc(t("contribution")) + '</td><td class="r">' + d(w.contribution, a.contribution, money2, true) + "</td></tr><tr><td>" + esc(t("break-even/day")) + '</td><td class="r">' +
          (w.breakeven_per_day == null ? t("never") : d(Math.ceil(w.breakeven_per_day), Math.ceil(a.breakeven_per_day), v => Math.round(v).toLocaleString(LOC()), false)) + "</td></tr><tr><td>" + esc(t("year 1 profit")) + '</td><td class="r">' + d(w.year1_profit, a.year1_profit, money, true) +
          "</td></tr><tr><td>" + esc(t("cash needed")) + '</td><td class="r">' + d(w.cash_needed, a.cash_needed, money, false) + "</td></tr><tr><td>" + esc(t("payback")) + '</td><td class="r">' + (w.payback_month ? t("month {m}", { m: w.payback_month }) : t("not in year 1")) + "</td></tr></table>";
      } catch (e) { $("#wi-out").innerHTML = '<div class="banner warn">' + esc(e.message) + "</div>"; }
    };
    $$("input[data-s]", el).forEach(inp => inp.oninput = () => {
      ui[inp.dataset.s] = +inp.value;
      inp.closest(".slider").querySelector("b").textContent = inp.dataset.s === "price" ? money2(+inp.value) : inp.value + "%";
      clearTimeout(timer); timer = setTimeout(recalc, 120);
    });
    $("#wi-reset").onclick = () => { S.ui.cfo = null; VIEWS.cfo(el); };
    recalc();
  };
  function slider(key, label, min, max, step, val, f) {
    return '<div class="slider"><label><span>' + esc(label) + "</span><b class=\"num\">" + esc(f(val)) + '</b></label><input type="range" data-s="' + key + '" min="' + min + '" max="' + max + '" step="' + step + '" value="' + val + '"></div>';
  }
  function items(title, list) {
    const total = (list || []).reduce((s, x) => s + (+x.cost || 0), 0);
    return '<div class="card"><h3>' + esc(title) + '</h3><table class="t">' + (list || []).map(x => "<tr><td>" + esc(x.label) + '</td><td class="r">' + money(+x.cost, total < 100 ? 2 : 0) + "</td></tr>").join("") +
      '<tr><td><b>' + esc(t("total")) + '</b></td><td class="r"><b>' + money(total, total < 100 ? 2 : 0) + "</b></td></tr></table></div>";
  }

  // ── docs ─────────────────────────────────────────────────────────────────────
  VIEWS.docs = async el => {
    const docs = S.st.docs;
    if (!docs.length) { el.innerHTML = empty(esc(t("Nothing written yet."))); return; }
    const cur = S.sub ? decodeURIComponent(S.sub) : (docs.find(d => d.path === "business-plan.md") || docs.find(d => d.path.endsWith(".md")) || docs[0]).path;
    const groups = {};
    docs.forEach(d => { const g = d.step || "other"; (groups[g] = groups[g] || []).push(d); });
    const order = ["board", "competitors", "consumer", "pricing", "offer", "cfo", "marketing", "brand", "ops", "launch", "plan", "feedback", "other"];
    let list = order.filter(g => groups[g]).map(g => '<div class="grp">' + esc(g === "other" || g === "feedback" ? t(g) : stepName(g)) + "</div>" + groups[g].map(d =>
      '<a href="#/p/' + S.pid + "/docs/" + encodeURIComponent(d.path) + (S.query.round ? "?round=" + encodeURIComponent(S.query.round) : "") + '" class="' + (d.path === cur ? "on" : "") + '"><span>' + esc(d.path) + "</span><small>" + esc(ago(d.mtime)) + "</small></a>").join("")).join("");
    el.innerHTML = '<div class="docs"><nav class="doclist">' + list + '</nav><div class="card" id="docview">…</div></div>';
    const meta = docs.find(d => d.path === cur) || {};
    try {
      const f = await api(fileUrl(cur));
      let body;
      if (cur.endsWith(".csv")) {
        const rows = MD.csvTable(f.text);
        body = '<div class="table-wrap"><table class="t"><thead><tr><th>' + (rows[0] || []).map(esc).join("</th><th>") + "</th></tr></thead><tbody>" + rows.slice(1).map(r => "<tr><td>" + r.map(esc).join("</td><td>") + "</td></tr>").join("") + "</tbody></table></div>";
      } else if (cur.endsWith(".json")) {
        let pretty = f.text; try { pretty = JSON.stringify(JSON.parse(f.text), null, 2); } catch (e) { /* show as is */ }
        body = '<div class="md"><pre><code>' + esc(pretty) + "</code></pre></div>";
      } else body = doc(f.text, cur, meta.step);
      $("#docview").innerHTML = '<div class="card-head"><h2 class="num" style="font-family:var(--mono);font-size:14px">' + esc(cur) + "</h2><small>" + (meta.step && meta.step !== "feedback" ? esc(stepName(meta.step)) + " · " : "") + esc(ago(f.mtime)) + "</small></div>" +
        (meta.step && !SNAP && !S.query.round && cur.endsWith(".md") ? '<p class="muted" style="font-size:12px;margin-top:-4px">' + esc(t("Hover a paragraph and press 💬 to leave feedback the skill will read next time.")) + "</p>" : "") + body;
    } catch (e) { $("#docview").innerHTML = empty(esc(e.message)); }
  };

  // ── feedback (phase 3) ───────────────────────────────────────────────────────
  VIEWS.feedback = async el => {
    const all = await api(P("feedback"));
    const pre = S.query.step || S.ui.fbStep || "board";
    let h = "";
    if (!SNAP && !S.query.round) h += '<form class="card" id="fb-add" style="margin-bottom:14px"><h2>' + esc(t("New feedback")) + '</h2><div class="form-row" style="margin:10px 0"><label class="field"><span>' + esc(t("for the step")) + '</span><select name="step">' +
      Object.keys(all).map(k => '<option value="' + k + '"' + (k === pre ? " selected" : "") + ">" + esc(stepName(k)) + "</option>").join("") + '</select></label><label class="field"><span>' + esc(t("kind")) + '</span><select name="kind">' +
      ["change", "keep", "question"].map(k => '<option value="' + k + '">' + esc(t("kind." + k)) + "</option>").join("") + '</select></label></div><textarea name="text" placeholder="' + esc(t("e.g. Test a $5.50 small size; the panel says $6.50 is steep for a daily drink.")) + '"></textarea>' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px;gap:10px;flex-wrap:wrap"><small class="muted">' + esc(t("Saved in founder/feedback/<step>.md. Every skill reads its file before it starts and moves items to Addressed.")) +
      '</small><button class="btn primary">' + esc(t("Save feedback")) + "</button></div></form>";
    const steps = Object.entries(all).filter(([, f]) => f.open.length || f.addressed.length);
    if (!steps.length) h += empty(esc(t("No feedback yet. Leave some here, or with 💬 on any paragraph in Docs, Board or the other views.")));
    h += '<div class="grid g2">' + steps.map(([k, f]) => '<div class="card"><div class="card-head"><h2>' + esc(stepName(k)) + "</h2>" + chip(f.open.length ? "warn" : "done", t("{o} open · {a} addressed", { o: f.open.length, a: f.addressed.length })) + "</div>" +
      fbList(k, f.open, false) + (f.addressed.length ? '<h3 style="margin:14px 0 6px;font-size:13px" class="muted">' + esc(t("Addressed")) + "</h3>" + fbList(k, f.addressed, true) : "") +
      (SNAP || S.query.round || !f.open.length ? "" : '<div style="margin-top:10px;display:flex;gap:6px;align-items:center"><a class="btn sm primary" href="#/p/' + S.pid + "/runs?step=" + k + '">▶ ' + esc(t("Re-run with this feedback")) + '</a><code class="copy" data-copy="' + esc(cmd(k)) + '">' + esc(cmd(k)) + "</code></div>") + "</div>").join("") + "</div>";
    el.innerHTML = h;
    const form = $("#fb-add");
    if (form) {
      form.step.onchange = () => { S.ui.fbStep = form.step.value; };
      form.onsubmit = async e => {
        e.preventDefault();
        try { await api("/api/p/" + S.pid + "/feedback/" + form.step.value, { method: "POST", body: { kind: form.kind.value, text: form.text.value } }); S.ui.fbStep = form.step.value; toast(t("Feedback saved")); refreshState(); VIEWS.feedback(el); }
        catch (err) { toast(err.message); }
      };
    }
    $$("[data-fb]", el).forEach(b => b.onclick = async () => {
      const [step, action, idx] = b.dataset.fb.split(":");
      try { await api("/api/p/" + S.pid + "/feedback/" + step, { method: "POST", body: { action: action === "remove-done" ? "remove" : action, index: +idx, addressed: action === "remove-done" } }); refreshState(); VIEWS.feedback(el); }
      catch (err) { toast(err.message); }
    });
  };
  function fbList(step, list, done) {
    if (!list.length) return '<p class="muted">' + esc(t("Nothing open.")) + "</p>";
    return '<ul class="checks">' + list.map((it, i) => '<li><span class="ic ' + (done ? "ok" : "ko") + '" style="' + (done ? "" : "background:var(--warn-soft);color:var(--warn)") + '">' + (done ? "✓" : "•") + '</span><div style="flex:1;min-width:0">' +
      chip("", t("kind." + it.kind)) + " " + MD.inline(it.text) + (it.ref ? '<div class="muted" style="font-size:11.5px">' + esc(t("on")) + " " + esc(it.ref) + "</div>" : "") + "</div>" +
      (SNAP || S.query.round ? "" : '<span style="display:flex;gap:4px">' + (done ? '<button class="btn sm" data-fb="' + step + ":reopen:" + i + '">' + esc(t("Reopen")) + "</button>" : '<button class="btn sm" data-fb="' + step + ":resolve:" + i + '" title="' + esc(t("Mark addressed")) + '">✓</button>') +
        '<button class="btn sm danger" data-fb="' + step + ":" + (done ? "remove-done" : "remove") + ":" + i + '" title="' + esc(t("Delete")) + '">✕</button></span>') + "</li>").join("") + "</ul>";
  }

  // ── rounds (phase 2) ─────────────────────────────────────────────────────────
  VIEWS.rounds = async el => {
    const list = await api("/api/p/" + S.pid + "/rounds");
    const ui = S.ui.rounds = S.ui.rounds || { a: list[0] ? list[0].id : "current", b: "current" };
    const rows = [["verdict", m => t(m.verdict || "n/a")], ["buy rate", m => pct(m.buy_rate)], ["price", m => money2(m.price)], ["contribution", m => money2(m.contribution)],
      ["margin at plan", m => pct(m.margin_at_plan)], ["break-even/day", m => intf(m.breakeven_per_day)], ["year 1 profit", m => money(m.year1_profit)], ["cash needed", m => money(m.cash_needed)],
      ["payback", m => m.payback_month ? t("month {m}", { m: m.payback_month }) : "n/a"], ["acceptable price", m => m.price_range && m.price_range[0] != null ? t("{a} to {b}", { a: money2(m.price_range[0]), b: money2(m.price_range[1]) }) : "n/a"],
      ["board score", m => m.board_score != null ? m.board_score.toFixed(1) : "n/a"]];
    let h = '<form class="card" id="round-add" style="margin-bottom:14px;display:flex;gap:10px;align-items:end;flex-wrap:wrap"><label class="field" style="flex:1;min-width:220px"><span>' + esc(t("Save the current state as a round")) +
      '</span><input type="text" name="label" placeholder="' + esc(t("e.g. Pitch v1, before the offer")) + '"></label><button class="btn primary">◷ ' + esc(t("Save round")) + "</button></form>";
    h += '<div class="banner info">' + esc(t("A round is a dated copy of founder/. To test two versions (two pitches, two prices), run one, save a round, change it, run again. Do not run two sessions in the same folder.")) + "</div>";
    if (!list.length) h += empty(esc(t("No rounds yet.")));
    else {
      h += '<div class="card table-wrap"><table class="t"><thead><tr><th>' + esc(t("round")) + "</th>" + rows.map(r => '<th class="r">' + esc(t(r[0])) + "</th>").join("") + "<th></th></tr></thead><tbody>" +
        list.map(r => "<tr><td><b>" + esc(r.label) + "</b><br><small>" + esc(new Date(r.created * 1000).toLocaleString(LOC())) + "</small></td>" + rows.map(x => '<td class="r">' + esc(x[1](r.metrics)) + "</td>").join("") +
          '<td><a class="btn sm" href="#/p/' + S.pid + "/pipeline?round=" + encodeURIComponent(r.id) + '">' + esc(t("View")) + "</a></td></tr>").join("") + "</tbody></table></div>";
      const opts = cur => ['<option value="current"' + (cur === "current" ? " selected" : "") + ">" + esc(t("current")) + "</option>"].concat(list.map(r => '<option value="' + esc(r.id) + '"' + (r.id === cur ? " selected" : "") + ">" + esc(r.label) + "</option>")).join("");
      h += '<div class="card" style="margin-top:14px"><div class="card-head"><h2>' + esc(t("Compare")) + '</h2><div style="display:flex;gap:8px;align-items:center"><select id="ra" style="width:auto">' + opts(ui.a) + '</select>→<select id="rb" style="width:auto">' + opts(ui.b) + '</select></div></div><div id="cmp">…</div></div>';
    }
    el.innerHTML = h;
    $("#round-add").onsubmit = async e => {
      e.preventDefault();
      try { const r = await api("/api/p/" + S.pid + "/rounds", { method: "POST", body: { label: e.target.label.value } }); ui.a = r.id; toast(t("Round saved")); VIEWS.rounds(el); } catch (err) { toast(err.message); }
    };
    if (!list.length) return;
    const cmp = async () => {
      const c = await api("/api/p/" + S.pid + "/rounds/compare?a=" + encodeURIComponent(ui.a) + "&b=" + encodeURIComponent(ui.b));
      const delta = (k, a, b) => {
        if (a == null || b == null || typeof a !== "number" || typeof b !== "number" || a === b) return "";
        const bad = ["breakeven_per_day", "cash_needed", "payback_month"].includes(k);
        return ' <small class="' + ((b > a) !== bad ? "up" : "down") + '">' + (b > a ? "▲" : "▼") + "</small>";
      };
      const keys = { "verdict": "verdict", "buy rate": "buy_rate", "price": "price", "contribution": "contribution", "margin at plan": "margin_at_plan", "break-even/day": "breakeven_per_day", "year 1 profit": "year1_profit",
        "cash needed": "cash_needed", "payback": "payback_month", "acceptable price": "price_range", "board score": "board_score" };
      let x = '<table class="t"><thead><tr><th></th><th class="r">' + esc(c.a.id === "current" ? t("current") : c.a.label) + '</th><th class="r">' + esc(c.b.id === "current" ? t("current") : c.b.label) + "</th></tr></thead><tbody>" +
        rows.map(r => "<tr><td>" + esc(t(r[0])) + '</td><td class="r">' + esc(r[1](c.a.metrics)) + '</td><td class="r">' + esc(r[1](c.b.metrics)) + delta(keys[r[0]], c.a.metrics[keys[r[0]]], c.b.metrics[keys[r[0]]]) + "</td></tr>").join("") + "</tbody></table>";
      const ch = Object.entries(c.changed);
      x += '<h3 style="margin:16px 0 8px">' + esc(t("{n} documents changed", { n: ch.length })) + "</h3>" + ch.map(([f, d]) => '<details style="margin-bottom:6px"><summary><code>' + esc(f) + "</code> " + (d.added ? chip("good", t("new")) : d.removed ? chip("bad", t("removed")) : "") + '</summary><div class="diff">' +
        d.diff.map(l => '<div class="' + (l[0] === "+" ? "add" : l[0] === "-" ? "del" : l[0] === "@" ? "hunk" : "") + '">' + esc(l) + "</div>").join("") + "</div></details>").join("");
      $("#cmp").innerHTML = x;
    };
    $("#ra").onchange = e => { ui.a = e.target.value; cmp(); };
    $("#rb").onchange = e => { ui.b = e.target.value; cmp(); };
    cmp().catch(e => { $("#cmp").innerHTML = empty(esc(e.message)); });
  };

  // ── runs (phase 4) ───────────────────────────────────────────────────────────
  VIEWS.runs = async el => {
    const r = await api("/api/p/" + S.pid + "/runs");
    const rid = S.sub;
    let h = '<div class="runs"><div class="runlist"><a href="#/p/' + S.pid + '/runs" class="' + (!rid ? "on" : "") + '"><b>＋ ' + esc(t("New run")) + "</b></a>" +
      r.runs.map(x => '<a href="#/p/' + S.pid + "/runs/" + esc(x.id) + '" class="' + (x.id === rid ? "on" : "") + '"><div style="display:flex;justify-content:space-between;gap:6px"><b>' + esc(stepName(x.step)) + "</b>" + chip(runCls(x.status), t("run." + x.status)) + "</div>" +
        '<div class="meta"><span>' + esc(ago(x.created)) + "</span><span>" + x.turns.length + " " + esc(t("turns")) + "</span>" + (x.cost ? "<span>$" + x.cost.toFixed(2) + "</span>" : "") + "</div></a>").join("") + '</div><div id="rundetail"></div></div>';
    el.innerHTML = h;
    const box = $("#rundetail");
    if (!rid) return newRun(box, r);
    const d = await api("/api/p/" + S.pid + "/runs/" + rid);
    if (!box.isConnected) return;  // a newer render replaced this one while we waited
    S.run = d.run.id;
    box.innerHTML = '<div class="card"><div class="card-head"><div><h2>' + esc(stepName(d.run.step)) + ' <small class="num">' + esc(d.run.id) + "</small></h2><small>" + esc(t("mode {m}", { m: d.run.mode })) + (d.run.session ? " · session " + esc(d.run.session.slice(0, 8)) : "") + "</small></div><div style=\"display:flex;gap:6px\">" + chip(runCls(d.run.status), t("run." + d.run.status)) +
      (d.run.status === "running" ? '<button class="btn sm danger" id="cancel">' + esc(t("Stop")) + "</button>" : "") + '</div></div><div class="log" id="log">' + d.events.map(evHtml).join("") + "</div>" + replyBox(d.run) + "</div>";
    const logEl = $("#log", box);
    if (d.run.status === "running" && logEl.lastElementChild) logEl.lastElementChild.scrollIntoView({ block: "end" });
    const c = $("#cancel");
    if (c) c.onclick = () => api("/api/p/" + S.pid + "/runs/" + rid + "/cancel", { method: "POST" }).catch(e => toast(e.message));
    const f = $("#reply");
    if (f) f.onsubmit = async e => {
      e.preventDefault();
      const allow = $$("input[name=allow]:checked", f).map(x => x.value);
      try { await api("/api/p/" + S.pid + "/runs/" + rid + "/reply", { method: "POST", body: { message: f.message.value, allow } }); VIEWS.runs(el); }
      catch (err) { toast(err.message); }
    };
  };
  const runCls = s => ({ running: "running", starting: "running", done: "done", waiting: "warn", failed: "failed", cancelled: "", interrupted: "warn" }[s] || "");

  function newRun(box, r) {
    const chk = r.check, step = S.query.step || "board";
    let h = '<form class="card" id="newrun"><h2>' + esc(t("Run a step from here")) + '</h2><p class="muted" style="font-size:12.5px">' +
      esc(t("Starts claude -p in the project folder with this repo's skills. Headless: the skill cannot ask you mid-run, so it lists its questions at the end and you answer below.")) + "</p>";
    if (!chk.claude) h += '<div class="banner warn">' + esc(t("The claude command is not on PATH for the GUI server.")) + "</div>";
    if (chk.lock) h += '<div class="banner run">' + esc(t("{s} is already running from the GUI. One GUI run per project at a time.", { s: stepName(chk.lock.step) })) + ' <a class="btn sm" href="#/p/' + S.pid + "/runs/" + esc(chk.lock.run) + '">' + esc(t("Follow")) + "</a></div>";
    if (chk.sessions.length) h += '<div class="banner warn"><span>⚠ ' + esc(t("{n} Claude session(s) already open in this folder (PID {p}). If one of them is running a skill, a run here can overwrite its files.", { n: chk.sessions.length, p: chk.sessions.map(s => s.pid).join(", ") })) +
      '</span><label style="display:flex;gap:6px;align-items:center"><input type="checkbox" name="force"> ' + esc(t("run anyway")) + "</label></div>";
    h += '<div class="form-row" style="margin:12px 0"><label class="field"><span>' + esc(t("step")) + '</span><select name="step">' + S.st.steps.map(s => '<option value="' + s.key + '"' + (s.key === step ? " selected" : "") + ">" + esc(stepName(s.key)) + " · " + esc(t("status." + s.status)) + "</option>").join("") +
      '</select></label><label class="field"><span>' + esc(t("permission mode")) + '</span><select name="mode">' + r.defaults.modes.map(m => '<option value="' + m + '">' + esc(m) + "</option>").join("") + "</select></label></div>" +
      '<label class="field"><span>' + esc(t("extra instructions or arguments (optional)")) + '</span><textarea name="extra" placeholder="' + esc(t("e.g. --quick, or: the business is a matcha café in Toronto, $6.50 a cup")) + '"></textarea></label>';
    const fb = (S.st.feedback || {})[step];
    if (fb && fb.open) h += '<div class="banner info" style="margin-top:10px">💬 ' + esc(t("{n} open feedback item(s) for this step will be read by the skill.", { n: fb.open })) + "</div>";
    h += '<details style="margin:10px 0"><summary class="link">' + esc(t("Allowed tools")) + '</summary><div class="allow" style="margin-top:8px">' + r.defaults.allowed.map(a => "<label>" + esc(a) + "</label>").join("") +
      '</div><label class="field" style="margin-top:8px"><span>' + esc(t("more, space separated")) + '</span><input type="text" name="allow" placeholder="Bash(git:*)"></label><label style="display:flex;gap:6px;align-items:center;margin-top:8px;font-size:12.5px"><input type="checkbox" name="use_local_skills" checked> ' +
      esc(t("load the skills from this repo (--plugin-dir), so they read founder/feedback")) + "</label></details>" +
      '<div style="display:flex;justify-content:flex-end"><button class="btn primary"' + (chk.lock || !chk.claude ? " disabled" : "") + ">▶ " + esc(t("Start")) + "</button></div></form>";
    box.innerHTML = h;
    const f = $("#newrun");
    f.step.onchange = () => { S.query.step = f.step.value; newRun(box, r); };
    f.onsubmit = async e => {
      e.preventDefault();
      try {
        const run = await api("/api/p/" + S.pid + "/runs", { method: "POST", body: { step: f.step.value, mode: f.mode.value, extra: f.extra.value, allow: f.allow.value.split(/\s+/).filter(Boolean),
          use_local_skills: f.use_local_skills.checked, force: f.force ? f.force.checked : false } });
        go("runs", run.id);
      } catch (err) { toast(err.message); }
    };
  }

  function evHtml(e) {
    const sub = e.sub ? " sub" : "";
    switch (e.t) {
      case "prompt": return '<div class="ev prompt">› ' + esc(e.text) + "</div>";
      case "init": return '<div class="ev muted" style="font-size:12px">' + esc(t("session started")) + " · " + esc(e.model || "") + "</div>";
      case "text": return '<div class="ev text' + sub + '">' + doc(e.text) + "</div>";
      case "tool": {
        const inp = e.input || {}, brief = inp.command || inp.file_path || inp.description || inp.pattern || inp.url || inp.query || inp.prompt || "";
        return '<details class="ev tool' + sub + '" data-tool="' + esc(e.id || "") + '"><summary><span class="tn">' + esc(e.name) + '</span><span class="ti">' + esc(String(brief).split("\n")[0]) + '</span><span class="res-ic"></span></summary><pre>' + esc(JSON.stringify(inp, null, 2)) + "</pre></details>";
      }
      case "result": return '<div class="ev tool-result" data-for="' + esc(e.id || "") + '" hidden data-err="' + (e.error ? 1 : 0) + '">' + esc(e.text) + "</div>";
      case "stderr": return '<div class="ev stderr">' + esc(e.text) + "</div>";
      case "done": return '<div class="ev done">' + chip(e.ok ? "done" : "failed", e.ok ? t("turn finished") : t("turn failed")) + (e.cost != null ? "<span>$" + (+e.cost).toFixed(3) + "</span>" : "") + (e.turns ? "<span>" + e.turns + " " + esc(t("model turns")) + "</span>" : "") +
        (e.denials && e.denials.length ? '<span class="down">' + esc(t("{n} tool call(s) blocked", { n: e.denials.length })) + "</span>" : "") + "</div>";
      default: return "";
    }
  }
  // attach tool results to their tool call blocks after rendering
  const linkResults = root => $$(".tool-result", root).forEach(r => {
    const tool = root.querySelector('[data-tool="' + CSS.escape(r.dataset.for) + '"]');
    if (tool && !tool.dataset.linked) {
      tool.dataset.linked = 1;
      tool.insertAdjacentHTML("beforeend", "<pre>" + r.innerHTML + "</pre>");
      if (r.dataset.err === "1") tool.classList.add("err");
      $(".res-ic", tool).textContent = r.dataset.err === "1" ? "✗" : "✓";
    }
  });
  new MutationObserver(() => { const l = $("#log"); if (l) linkResults(l); }).observe(document.body, { childList: true, subtree: true });

  function replyBox(run) {
    if (["running", "starting"].includes(run.status) || !run.session) return "";
    const sug = run.suggested_allow || [];
    return '<form class="reply" id="reply">' + (run.questions ? '<div class="banner info">' + esc(t("The skill asked you something. Answer below and it continues in the same session.")) + "</div>" : "") +
      (sug.length ? '<div class="allow"><span>' + esc(t("Blocked tools, allow and continue:")) + "</span>" + sug.map(a => '<label><input type="checkbox" name="allow" value="' + esc(a) + '" checked> ' + esc(a) + "</label>").join("") + "</div>" : "") +
      '<textarea name="message" placeholder="' + esc(run.questions ? t("Your answers…") : t("Ask for a change, or say continue…")) + '"></textarea><div style="display:flex;justify-content:flex-end"><button class="btn primary">' + esc(t("Send")) + "</button></div></form>";
  }

  // ── live updates ─────────────────────────────────────────────────────────────
  let refreshTimer = null, lastTouched = [];
  function typing() {
    const a = document.activeElement;
    return a && $("#main").contains(a) && (a.tagName === "TEXTAREA" || (a.tagName === "INPUT" && a.type === "text") || a.tagName === "SELECT");
  }
  async function refreshState() {
    try { S.st = await api(P("state")); } catch (e) { return; }
    const hdr = $("#hdr");
    if (!hdr) return;
    hdr.innerHTML = header();
    bindHeader();
  }
  // throttled, not debounced: while a skill writes, events arrive every second and a debounce would never fire
  function scheduleRefresh(touched) {
    lastTouched = lastTouched.concat(touched || []);
    if (refreshTimer) return;
    refreshTimer = setTimeout(async () => {
      refreshTimer = null;
      if (typing() || !$("#drawer").hidden) { scheduleRefresh(); return; }
      const t2 = lastTouched; lastTouched = [];
      await refreshState();
      const rel = TAB_STEPS[S.tab];
      if (["pipeline", "docs", "feedback"].includes(S.tab) || !rel || rel.some(k => t2.includes(k)) || !t2.length) renderView();
    }, 500);
  }
  function connect() {
    if (SNAP || !window.EventSource) return;
    const es = new EventSource("/api/events");
    let opened = false;
    es.onopen = () => { if (opened) { loadProjects(); if (S.pid) scheduleRefresh(); } opened = true; };  // resync after the hub restarts
    es.onmessage = m => {
      let msg; try { msg = JSON.parse(m.data); } catch (e) { return; }
      const d = msg.data;
      if (msg.kind === "files") {
        if (!connect._p) connect._p = setTimeout(() => { connect._p = null; loadProjects(); }, 1500);
        if (d.project === S.pid && !S.query.round) scheduleRefresh(d.steps);
      } else if (msg.kind === "run_event" && d.project === S.pid && S.tab === "runs" && S.run === d.run) {
        const log = $("#log");
        if (log) { const near = window.innerHeight + window.scrollY > document.body.scrollHeight - 200; log.insertAdjacentHTML("beforeend", evHtml(d.event)); if (near) window.scrollTo(0, document.body.scrollHeight); }
      } else if (msg.kind === "run" && d.project === S.pid) {
        refreshState();
        if (S.tab === "runs") renderView();
        if (d.run.status === "waiting") toast(t("{s} is waiting for you", { s: stepName(d.run.step) }));
      }
    };
  }

  // ── chrome ───────────────────────────────────────────────────────────────────
  function applyTheme() {
    const th = store("fg-theme") || "auto";
    if (th === "auto") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", th);
    $("#theme").textContent = { auto: "◐ auto", light: "☀ light", dark: "☾ dark" }[th];
  }
  $("#theme").onclick = () => { const order = ["auto", "light", "dark"]; store("fg-theme", order[(order.indexOf(store("fg-theme") || "auto") + 1) % 3]); applyTheme(); };
  $("#lang").onclick = () => { I18N.set(I18N.lang === "pt" ? "en" : "pt"); store("fg-lang", I18N.lang); applyLang(); render(); };
  function applyLang() {
    $("#lang").textContent = I18N.lang === "pt" ? "EN" : "PT";
    document.documentElement.lang = I18N.lang === "pt" ? "pt-BR" : "en";
    $$("[data-i18n]").forEach(n => { n.textContent = t(n.dataset.i18n); });
  }
  $("#add-project").onsubmit = async e => {
    e.preventDefault();
    const path = e.target.path.value.trim();
    if (!path) return;
    try { const p = await api("/api/projects", { method: "POST", body: { path } }); e.target.path.value = ""; await loadProjects(); location.hash = "#/p/" + p.id + "/pipeline"; }
    catch (err) { toast(err.message); }
  };
  if (SNAP) $("#add-project").hidden = true;

  I18N.set(store("fg-lang") || (navigator.language || "en").slice(0, 2));
  applyLang(); applyTheme();
  window.addEventListener("hashchange", () => { S.run = null; render(); });
  loadProjects().then(() => {
    if (!location.hash && S.projects.length === 1) location.hash = "#/p/" + S.projects[0].id + "/pipeline";
    else render();
  });
  connect();
})();
