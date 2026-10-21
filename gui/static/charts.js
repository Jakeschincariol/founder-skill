/* Hand-written SVG charts, no library: lines with markers (price curves),
   bars with an optional line (year 1), and a scatter (competitors).
   Colours come from CSS classes so light and dark themes both work. */
(function () {
  "use strict";
  const esc = s => window.MD.esc(s);
  const W = 720;

  function scale(d0, d1, r0, r1) {
    const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
    return v => r0 + (v - d0) * k;
  }

  function ticks(lo, hi, n) {
    if (hi === lo) return [lo];
    const raw = (hi - lo) / n;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(x => x * mag).find(x => x >= raw) || raw;
    const out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  }

  function frame(H, pad, xs, ys, xt, yt, xfmt, yfmt) {
    let g = '<g class="grid">';
    for (const t of yt) g += '<line x1="' + pad.l + '" x2="' + (W - pad.r) + '" y1="' + ys(t) + '" y2="' + ys(t) + '"/>';
    g += "</g><g class=\"axis\">";
    for (const t of yt) g += '<text x="' + (pad.l - 6) + '" y="' + (ys(t) + 4) + '" text-anchor="end">' + esc(yfmt(t)) + "</text>";
    for (const t of xt) g += '<text x="' + xs(t) + '" y="' + (H - pad.b + 16) + '" text-anchor="middle">' + esc(xfmt(t)) + "</text>";
    return g + "</g>";
  }

  /* spec: {x:[...], series:[{name, values, cls}], markers:[{x, label, cls}], band:[x0,x1], dots:[{x, label}],
            xfmt, yfmt, height, ymin, ymax} */
  function line(el, spec) {
    const H = spec.height || 300, pad = { l: 48, r: 16, t: 28, b: 28 };
    const xs0 = spec.x, lo = xs0[0], hi = xs0[xs0.length - 1];
    const all = spec.series.flatMap(s => s.values).filter(v => v != null);
    const ymin = spec.ymin != null ? spec.ymin : Math.min(0, ...all), ymax = spec.ymax != null ? spec.ymax : Math.max(...all);
    const xs = scale(lo, hi, pad.l, W - pad.r), ys = scale(ymin, ymax, H - pad.b, pad.t);
    const xfmt = spec.xfmt || (v => v), yfmt = spec.yfmt || (v => v);
    let s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc(spec.label || "chart") + '">';
    if (spec.band && spec.band[0] != null && spec.band[1] != null)
      s += '<rect class="band" x="' + xs(spec.band[0]) + '" y="' + pad.t + '" width="' + Math.max(0, xs(spec.band[1]) - xs(spec.band[0])) + '" height="' + (H - pad.t - pad.b) + '"/>';
    s += frame(H, pad, xs, ys, ticks(lo, hi, 8), ticks(ymin, ymax, 5), xfmt, yfmt);
    spec.series.forEach((se, k) => {
      const pts = se.values.map((v, i) => v == null ? null : xs(xs0[i]).toFixed(1) + "," + ys(v).toFixed(1)).filter(Boolean);
      s += '<polyline fill="none" stroke-width="2.2" stroke-linejoin="round" class="' + (se.cls || "s" + (k + 1)) + '"' + (se.dash ? ' stroke-dasharray="5 4"' : "") + ' points="' + pts.join(" ") + '"/>';
    });
    (spec.markers || []).forEach((m, k) => {
      if (m.x == null || m.x < lo || m.x > hi) return;
      const x = xs(m.x);
      s += '<line class="marker ' + (m.cls || "") + '" x1="' + x + '" x2="' + x + '" y1="' + pad.t + '" y2="' + (H - pad.b) + '"/>';
      s += '<text x="' + x + '" y="' + (pad.t - 8 - (k % 2) * 11) + '" text-anchor="middle" style="font-weight:600">' + esc(m.label) + "</text>";
    });
    (spec.dots || []).forEach(d => {
      if (d.x == null || d.x < lo || d.x > hi) return;
      s += '<circle class="comp" cx="' + xs(d.x) + '" cy="' + (H - pad.b - 5) + '" r="4.5"><title>' + esc(d.label) + "</title></circle>";
    });
    s += '<line class="hover-line" x1="0" x2="0" y1="' + pad.t + '" y2="' + (H - pad.b) + '" style="display:none"/>';
    s += '<rect x="' + pad.l + '" y="' + pad.t + '" width="' + (W - pad.l - pad.r) + '" height="' + (H - pad.t - pad.b) + '" fill="transparent" class="hit"/></svg>';
    el.classList.add("chart");
    el.innerHTML = s + '<div class="tip" hidden></div>' + keys(spec.series);
    hover(el, spec, xs, W, (i) => "<b>" + esc(xfmt(xs0[i])) + "</b><br>" + spec.series.map(se => esc(se.name) + ": <b>" + esc(yfmt(se.values[i])) + "</b>").join("<br>"),
      x => { let best = 0; xs0.forEach((v, i) => { if (Math.abs(xs(v) - x) < Math.abs(xs(xs0[best]) - x)) best = i; }); return best; }, i => xs(xs0[i]));
  }

  function keys(series) {
    return '<div class="keys">' + series.map((se, k) => '<span><i style="background:var(--c' + (k + 1) + ')"></i>' + esc(se.name) + "</span>").join("") + "</div>";
  }

  function hover(el, spec, xs, W, tipFn, pick, xAt) {
    const svg = el.querySelector("svg"), tip = el.querySelector(".tip"), ln = el.querySelector(".hover-line"), hit = el.querySelector(".hit");
    if (!hit) return;
    hit.addEventListener("mousemove", ev => {
      const r = svg.getBoundingClientRect(), x = (ev.clientX - r.left) * (W / r.width);
      const i = pick(x), px = xAt(i);
      if (ln) { ln.setAttribute("x1", px); ln.setAttribute("x2", px); ln.style.display = ""; }
      tip.hidden = false; tip.innerHTML = tipFn(i);
      tip.style.left = (px * r.width / W) + "px"; tip.style.top = (ev.clientY - r.top) + "px";
    });
    hit.addEventListener("mouseleave", () => { tip.hidden = true; if (ln) ln.style.display = "none"; });
  }

  /* spec: {labels, values, line:{name, values}, yfmt, height, ghost:[values]} */
  function bars(el, spec) {
    const H = spec.height || 260, pad = { l: 60, r: 16, t: 16, b: 28 };
    const n = spec.labels.length;
    const vals = spec.values.concat(spec.line ? spec.line.values : [], spec.ghost || []).filter(v => v != null);
    const ymin = Math.min(0, ...vals), ymax = Math.max(0, ...vals);
    const ys = scale(ymin, ymax, H - pad.b, pad.t), bw = (W - pad.l - pad.r) / n;
    const cx = i => pad.l + bw * i + bw / 2, yfmt = spec.yfmt || (v => v);
    let s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img">';
    s += frame(H, pad, cx, ys, [], ticks(ymin, ymax, 5), String, yfmt);
    spec.labels.forEach((l, i) => { s += '<text x="' + cx(i) + '" y="' + (H - pad.b + 16) + '" text-anchor="middle">' + esc(l) + "</text>"; });
    if (spec.ghost) spec.ghost.forEach((v, i) => {
      const y0 = ys(Math.max(0, v)), h = Math.abs(ys(v) - ys(0));
      s += '<rect class="ghost" x="' + (cx(i) - bw * .36) + '" y="' + y0 + '" width="' + bw * .72 + '" height="' + Math.max(h, 1) + '" rx="3"/>';
    });
    spec.values.forEach((v, i) => {
      const y0 = ys(Math.max(0, v)), h = Math.abs(ys(v) - ys(0));
      s += '<rect class="' + (v >= 0 ? "pos" : "neg") + '" x="' + (cx(i) - bw * .3) + '" y="' + y0 + '" width="' + bw * .6 + '" height="' + Math.max(h, 1) + '" rx="3"/>';
    });
    s += '<line x1="' + pad.l + '" x2="' + (W - pad.r) + '" y1="' + ys(0) + '" y2="' + ys(0) + '" style="stroke:var(--ink-3)"/>';
    if (spec.line) s += '<polyline fill="none" stroke-width="2" class="s2" points="' + spec.line.values.map((v, i) => cx(i) + "," + ys(v)).join(" ") + '"/>' +
      spec.line.values.map((v, i) => '<circle class="f2" cx="' + cx(i) + '" cy="' + ys(v) + '" r="3"/>').join("");
    s += '<line class="hover-line" x1="0" x2="0" y1="' + pad.t + '" y2="' + (H - pad.b) + '" style="display:none"/>';
    s += '<rect x="' + pad.l + '" y="' + pad.t + '" width="' + (W - pad.l - pad.r) + '" height="' + (H - pad.t - pad.b) + '" fill="transparent" class="hit"/></svg>';
    el.classList.add("chart");
    el.innerHTML = s + '<div class="tip" hidden></div><div class="keys"><span><i style="background:var(--accent)"></i>' + esc(spec.name || "") + "</span>" +
      (spec.line ? '<span><i style="background:var(--c2)"></i>' + esc(spec.line.name) + "</span>" : "") + (spec.ghostName ? '<span><i style="background:var(--line)"></i>' + esc(spec.ghostName) + "</span>" : "") + "</div>";
    hover(el, spec, null, W, i => "<b>" + esc(spec.labels[i]) + "</b><br>" + esc(spec.name || "") + ": <b>" + esc(yfmt(spec.values[i])) + "</b>" +
      (spec.line ? "<br>" + esc(spec.line.name) + ": <b>" + esc(yfmt(spec.line.values[i])) + "</b>" : "") +
      (spec.ghost ? "<br>" + esc(spec.ghostName || "") + ": <b>" + esc(yfmt(spec.ghost[i])) + "</b>" : ""),
      x => Math.max(0, Math.min(n - 1, Math.floor((x - pad.l) / bw))), cx);
  }

  /* spec: {points:[{x, y, label, cls}], xfmt, yfmt, xlabel, ylabel, height, vline:{x, label}} */
  function scatter(el, spec) {
    const H = spec.height || 260, pad = { l: 48, r: 24, t: 20, b: 40 };
    const pts = spec.points.filter(p => p.x != null && p.y != null);
    if (!pts.length) { el.innerHTML = '<div class="empty">no data</div>'; return; }
    const xv = pts.map(p => p.x).concat(spec.vline ? [spec.vline.x] : []).filter(v => v != null), yv = pts.map(p => p.y);
    const xl = Math.min(...xv), xh = Math.max(...xv), yl = Math.min(...yv), yh = Math.max(...yv);
    const px = (xh - xl) * .12 || 1, py = (yh - yl) * .15 || .5;
    const xs = scale(xl - px, xh + px, pad.l, W - pad.r), ys = scale(yl - py, yh + py, H - pad.b, pad.t);
    const xfmt = spec.xfmt || (v => v), yfmt = spec.yfmt || (v => v);
    let s = '<svg viewBox="0 0 ' + W + " " + H + '" role="img">';
    s += frame(H, pad, xs, ys, ticks(xl - px, xh + px, 6), ticks(yl - py, yh + py, 4), xfmt, yfmt);
    if (spec.vline && spec.vline.x != null) {
      s += '<line class="marker price" x1="' + xs(spec.vline.x) + '" x2="' + xs(spec.vline.x) + '" y1="' + pad.t + '" y2="' + (H - pad.b) + '"/>' +
        '<text x="' + (xs(spec.vline.x) + 5) + '" y="' + (pad.t + 10) + '" style="font-weight:600">' + esc(spec.vline.label) + "</text>";
    }
    pts.forEach((p, i) => {
      s += '<circle class="' + (p.cls || "f" + ((i % 5) + 1)) + '" cx="' + xs(p.x) + '" cy="' + ys(p.y) + '" r="7" opacity=".9"><title>' + esc(p.label + ": " + xfmt(p.x) + ", " + yfmt(p.y)) + "</title></circle>";
      s += '<text x="' + (xs(p.x) + 10) + '" y="' + (ys(p.y) + 4) + '">' + esc(p.label) + "</text>";
    });
    s += '<text x="' + (W / 2) + '" y="' + (H - 6) + '" text-anchor="middle">' + esc(spec.xlabel || "") + "</text>";
    s += '<text x="12" y="' + (H / 2) + '" transform="rotate(-90 12 ' + (H / 2) + ')" text-anchor="middle">' + esc(spec.ylabel || "") + "</text></svg>";
    el.classList.add("chart");
    el.innerHTML = s;
  }

  window.Charts = { line, bars, scatter };
})();
