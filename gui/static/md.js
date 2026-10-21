/* A small markdown renderer for what the skills write: headings, paragraphs,
   lists and task lists, tables, quotes, code, rules, bold, italic, code, links.
   Every top-level block is wrapped in .blk with its source text, so the docs
   view can attach feedback to it. Output is escaped; no raw HTML passes through. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  function inline(s) {
    const codes = [];
    s = s.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return "\u0000" + (codes.length - 1) + "\u0000"; });
    s = esc(s);
    s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (_, t, u) => {
      const safe = /^(https?:|mailto:|#|\/|\.)/i.test(u) ? u : "#";
      return '<a href="' + safe + '" target="_blank" rel="noopener">' + t + "</a>";
    });
    s = s.replace(/(^|[\s(])(https?:\/\/[^\s<)]+)/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/__([^_]+)__/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*\w])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>").replace(/(^|[^_\w])_([^_\s][^_]*)_(?!\w)/g, "$1<em>$2</em>");
    s = s.replace(/\u0000(\d+)\u0000/g, (_, i) => "<code>" + esc(codes[+i]) + "</code>");
    return s;
  }

  function isNum(c) { return /^[-$€£R]*\s?-?[\d,.]+%?\s*\w{0,4}$/.test(c.trim()) && /\d/.test(c); }

  function table(lines) {
    const split = l => l.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
    const head = split(lines[0]);
    const align = split(lines[1]).map(c => /:$/.test(c) ? "r" : "");
    const rows = lines.slice(2).map(split);
    let h = "<table><thead><tr>" + head.map((c, i) => '<th class="' + (align[i] || "") + '">' + inline(c) + "</th>").join("") + "</tr></thead><tbody>";
    for (const r of rows) h += "<tr>" + r.map((c, i) => '<td class="' + (align[i] || (isNum(c) ? "r" : "")) + '">' + inline(c) + "</td>").join("") + "</tr>";
    return h + "</tbody></table>";
  }

  function list(lines) {
    const ordered = /^\s*\d+[.)]\s/.test(lines[0]);
    let h = ordered ? "<ol>" : "<ul>";
    let depth0 = lines[0].match(/^\s*/)[0].length;
    let buf = [];
    const flush = () => {
      if (!buf.length) return;
      const first = buf[0].replace(/^\s*(?:[-*+]|\d+[.)])\s+/, "");
      const rest = buf.slice(1);
      const task = first.match(/^\[([ xX])\]\s+(.*)$/);
      const body = task ? '<input type="checkbox" disabled' + (task[1] !== " " ? " checked" : "") + "> " + inline(task[2]) : inline(first);
      h += "<li" + (task ? ' class="task"' : "") + ">" + body + (rest.length ? list(rest) : "") + "</li>";
      buf = [];
    };
    for (const l of lines) {
      const ind = l.match(/^\s*/)[0].length;
      if (ind <= depth0 && /^\s*(?:[-*+]|\d+[.)])\s/.test(l)) flush();
      buf.push(ind > depth0 ? l : l);
    }
    flush();
    return h + (ordered ? "</ol>" : "</ul>");
  }

  function blocks(text) {
    const lines = String(text || "").replace(/\r/g, "").split("\n");
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const l = lines[i];
      if (!l.trim()) { i++; continue; }
      let m;
      if ((m = l.match(/^```(\w*)/))) {
        const start = i; const buf = []; i++;
        while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
        i++;
        out.push({ src: lines.slice(start, i).join("\n"), html: "<pre><code>" + esc(buf.join("\n")) + "</code></pre>" });
      } else if ((m = l.match(/^(#{1,6})\s+(.*)$/))) {
        const n = Math.min(m[1].length, 4);
        out.push({ src: l, html: "<h" + n + ">" + inline(m[2]) + "</h" + n + ">", heading: m[2] });
        i++;
      } else if (/^\s*([-*_])\s*\1\s*\1[\s\1]*$/.test(l)) {
        out.push({ src: l, html: "<hr>" }); i++;
      } else if (/^\s*\|/.test(l) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
        const start = i;
        while (i < lines.length && /^\s*\|/.test(lines[i])) i++;
        out.push({ src: lines.slice(start, i).join("\n"), html: table(lines.slice(start, i)) });
      } else if (/^\s*>/.test(l)) {
        const start = i;
        while (i < lines.length && /^\s*>/.test(lines[i])) i++;
        const inner = lines.slice(start, i).map(x => x.replace(/^\s*>\s?/, "")).join("\n");
        out.push({ src: lines.slice(start, i).join("\n"), html: "<blockquote>" + render(inner) + "</blockquote>" });
      } else if (/^\s*(?:[-*+]|\d+[.)])\s+/.test(l)) {
        const start = i;
        while (i < lines.length && (/^\s*(?:[-*+]|\d+[.)])\s+/.test(lines[i]) || (/^\s{2,}\S/.test(lines[i]) && i > start))) i++;
        out.push({ src: lines.slice(start, i).join("\n"), html: list(lines.slice(start, i)) });
      } else {
        const start = i;
        while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|```|\s*>|\s*\||\s*(?:[-*+]|\d+[.)])\s)/.test(lines[i])) i++;
        if (i === start) i++;
        out.push({ src: lines.slice(start, i).join("\n"), html: "<p>" + lines.slice(start, i).map(inline).join("<br>") + "</p>" });
      }
    }
    return out;
  }

  function render(text, opts) {
    opts = opts || {};
    const bs = blocks(text);
    if (!opts.commentable) return bs.map(b => b.html).join("\n");
    let section = "";
    return bs.map((b, i) => {
      if (b.heading) section = b.heading;
      return '<div class="blk" data-i="' + i + '" data-section="' + esc(section) + '" data-src="' + esc(b.src.slice(0, 500)) + '">' + b.html +
        '<button class="btn sm cbtn" data-comment="' + i + '" title="Feedback">💬</button></div>';
    }).join("\n");
  }

  function csvTable(text) {
    const rows = [];
    for (const line of String(text || "").split(/\r?\n/)) {
      if (!line.trim()) continue;
      const cells = []; let cur = "", q = false;
      for (let j = 0; j < line.length; j++) {
        const c = line[j];
        if (q) { if (c === '"' && line[j + 1] === '"') { cur += '"'; j++; } else if (c === '"') q = false; else cur += c; }
        else if (c === '"') q = true; else if (c === ",") { cells.push(cur); cur = ""; } else cur += c;
      }
      cells.push(cur); rows.push(cells);
    }
    return rows;
  }

  window.MD = { render, inline, esc, csvTable };
})();
