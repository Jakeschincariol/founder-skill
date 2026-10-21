"""One project: a founder/ folder and everything the GUI reads out of it.

Nothing in here writes to founder/ except the GUI's own corner, founder/.gui/
(rounds, run logs, checklist ticks), and founder/feedback/ (phase 3), which the
skills read on purpose.
"""

import csv
import hashlib
import json
import os
import re

from . import steps, tools

GUI_DIRNAME = ".gui"
SKIP_DIRS = {GUI_DIRNAME, "__pycache__", ".git"}


class NotFound(Exception):
    pass


def resolve(path):
    """Accept a project folder or its founder/ folder. Returns (root, founder_dir)."""
    p = os.path.realpath(os.path.expanduser(path))
    if os.path.basename(p) == "founder" and not os.path.isdir(os.path.join(p, "founder")):
        return os.path.dirname(p), p
    return p, os.path.join(p, "founder")


def project_id(fdir):
    return hashlib.sha1(fdir.encode("utf-8")).hexdigest()[:10]


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError):
        return None


def _json(path):
    raw = _read(path)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _money(text):
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", text or "")
    return float(m.group(0).replace(",", "")) if m else None


class Project:
    def __init__(self, path):
        self.root, self.fdir = resolve(path)
        self.id = project_id(self.fdir)
        self.gdir = os.path.join(self.fdir, GUI_DIRNAME)

    # ── files ──────────────────────────────────────────────────────────────────
    def exists(self):
        return os.path.isdir(self.fdir)

    def path(self, rel):
        """A path inside founder/, refusing anything that escapes it."""
        full = os.path.realpath(os.path.join(self.fdir, rel))
        if full != self.fdir and not full.startswith(self.fdir + os.sep):
            raise NotFound(rel)
        return full

    def read(self, rel):
        return _read(self.path(rel))

    def scan(self):
        """{relpath: mtime} for every file in founder/, the GUI's own folder left out."""
        files = {}
        if not self.exists():
            return files
        for base, dirs, names in os.walk(self.fdir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for n in names:
                if n.startswith(".") and n != ".gitkeep":
                    continue
                full = os.path.join(base, n)
                try:
                    files[os.path.relpath(full, self.fdir).replace(os.sep, "/")] = os.path.getmtime(full)
                except OSError:
                    pass
        return files

    def name(self):
        idea = self.read("idea.md") if self.exists() else None
        if idea and idea.startswith("# "):
            return idea.splitlines()[0][2:].strip()
        nums = _json(os.path.join(self.fdir, "numbers.json"))
        if nums and nums.get("business"):
            return nums["business"]
        return os.path.basename(self.root)

    # ── overview ───────────────────────────────────────────────────────────────
    def state(self, active_runs=()):
        files = self.scan()
        st = steps.status(files, active_runs)
        verdict = self.verdict()
        docs = [{"path": p, "step": steps.owner(p) or ("feedback" if p.startswith("feedback/") else None),
                 "mtime": files[p]}
                for p in sorted(files) if p.endswith((".md", ".csv", ".json"))
                and not p.startswith(("panel/briefs/", "panel/answers/"))]
        return {
            "id": self.id, "name": self.name(), "root": self.root, "founder_dir": self.fdir,
            "exists": self.exists(), "steps": st, "next": steps.next_step(st),
            "verdict": verdict, "docs": docs, "file_count": len(files),
            "updated": max(files.values()) if files else None,
            "checklist": self.checklist(),
        }

    def verdict(self):
        if not os.path.exists(os.path.join(self.fdir, "numbers.json")) and \
                not os.path.exists(os.path.join(self.fdir, "panel", "results.json")):
            return {"verdict": "Incomplete", "checks": []}
        try:
            v, checks, _, _ = tools.compile_plan().verdict(self.fdir)
        except Exception as e:  # a half-written numbers.json should not take the page down
            return {"verdict": "Incomplete", "checks": [], "error": str(e)}
        return {"verdict": v, "checks": [{"ok": ok, "text": t} for ok, t in checks]}

    # ── board ──────────────────────────────────────────────────────────────────
    def board(self):
        memos = []
        bdir = os.path.join(self.fdir, "board")
        if os.path.isdir(bdir):
            for n in sorted(os.listdir(bdir)):
                if not n.endswith(".md") or n == "brief.md":
                    continue
                text = _read(os.path.join(bdir, n)) or ""
                m = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*(?:/\s*10)?\s*\|\s*Vote:\s*([A-Z ]+)", text)
                memos.append({
                    "lens": n[:-3], "file": "board/" + n, "text": text,
                    "score": float(m.group(1)) if m else None,
                    "vote": m.group(2).strip() if m else None,
                    "sections": _sections(text),
                })
        return {"idea": self.read("idea.md"), "summary": self.read("board.md"),
                "brief": self.read("board/brief.md"), "memos": memos, "checklist": self.checklist()}

    def checklist(self):
        """The board's conditions (markdown checkboxes in board.md) plus the ticks made in the GUI."""
        text = self.read("board.md") if self.exists() else None
        if not text:
            return []
        ticks = _json(os.path.join(self.gdir, "checklist.json")) or {}
        items = []
        for line in text.splitlines():
            m = re.match(r"^\s*[-*]\s*\[([ xX])\]\s*(.+)$", line)
            if m:
                cid = hashlib.sha1(m.group(2).strip().encode("utf-8")).hexdigest()[:8]
                tick = ticks.get(cid, {})
                items.append({"id": cid, "text": m.group(2).strip(),
                              "done": tick.get("done", m.group(1).lower() == "x"),
                              "note": tick.get("note", "")})
        return items

    def tick(self, cid, done, note=""):
        os.makedirs(self.gdir, exist_ok=True)
        path = os.path.join(self.gdir, "checklist.json")
        ticks = _json(path) or {}
        ticks[cid] = {"done": bool(done), "note": note}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(ticks, fh, indent=2)

    # ── competitors ────────────────────────────────────────────────────────────
    def competitors(self):
        rows = []
        raw = self.read("competitors.csv")
        if raw:
            for r in csv.DictReader(raw.splitlines()):
                r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
                r["price"] = _money(r.get("price_of_comparable_item"))
                r["rating_num"] = _money(r.get("rating"))
                rows.append(r)
        return {"rows": rows, "report": self.read("competitors.md")}

    # ── consumer panel ─────────────────────────────────────────────────────────
    def panel(self):
        pdir = os.path.join(self.fdir, "panel")
        state = _json(os.path.join(pdir, "panel.json"))
        cards = _json(os.path.join(pdir, "personas.json")) or []
        buyers = []
        answered = 0
        for c in cards:
            ans = _json(os.path.join(pdir, "answers", c["id"] + ".json"))
            ok = isinstance(ans, dict) and ans.get("id") == c["id"] and isinstance(ans.get("buys"), bool)
            answered += 1 if ok else 0
            buyers.append(dict(c, answer=ans if ok else None,
                               has_brief=os.path.exists(os.path.join(pdir, "briefs", c["id"] + ".md"))))
        results = _json(os.path.join(pdir, "results.json"))
        live = None
        if answered:
            try:
                live = tools.panel().tally(pdir)
            except Exception:
                live = None
        return tools.clean({
            "exists": state is not None, "seed": state and state.get("seed"),
            "n": len(cards), "answered": answered, "customer": state and state.get("customer"),
            "pitch": state and state.get("pitch"), "buyers": buyers,
            "results": results, "live": live, "report": self.read("panel/results.md") if self.exists() else None,
            "pitch_now": self.read("pitch.md"), "pitch_v1": self.read("pitch-v1.md"),
        })

    def brief(self, pid):
        if not re.match(r"^P\d{3,}$", pid):
            raise NotFound(pid)
        return self.read("panel/briefs/%s.md" % pid)

    # ── pricing ────────────────────────────────────────────────────────────────
    def pricing(self):
        vw = tools.pricing()
        out = {"report": self.read("pricing.md"), "curve_report": self.read("pricing-curve.md"),
               "price": None, "analysis": None, "curves": None, "dropped": 0,
               "competitors": [{"name": r.get("name"), "price": r["price"]}
                               for r in self.competitors()["rows"] if r.get("price")]}
        nums = _json(os.path.join(self.fdir, "numbers.json"))
        if nums:
            out["price"] = nums.get("price")
            try:
                out["variable_per_unit"] = tools.unit_economics().analyse(nums)["variable_per_unit"]
            except Exception:
                pass
        adir = os.path.join(self.fdir, "panel", "answers")
        if os.path.isdir(adir):
            rows, dropped = vw.read(adir)
            out["dropped"] = dropped
            out["n"] = len(rows)
            if len(rows) >= 5:
                res = vw.analyse(rows)
                lo = min(r[0] for r in rows)
                hi = max(r[3] for r in rows)
                grid = [lo + (hi - lo) * i / 120.0 for i in range(121)]
                tc, ch, ex, te = vw.curves(rows, grid)
                out["analysis"] = res
                out["curves"] = {"grid": grid, "too_cheap": tc, "cheap": ch, "expensive": ex, "too_expensive": te}
        return tools.clean(out)

    # ── cfo ────────────────────────────────────────────────────────────────────
    def numbers(self):
        return _json(os.path.join(self.fdir, "numbers.json"))

    def cfo(self):
        spec = self.numbers()
        out = {"spec": spec, "report": self.read("cfo.md"), "sources": self.read("cfo-sources.md"),
               "analysis": None, "sensitivity": None, "error": None}
        if spec:
            ue = tools.unit_economics()
            try:
                out["analysis"] = ue.analyse(spec)
                out["sensitivity"] = [{"label": label, "result": _brief_numbers(a)} for label, a in ue.sensitivity(spec)]
            except Exception as e:
                out["error"] = str(e)
        return tools.clean(out)

    def whatif(self, change):
        """Re-run unit_economics on a changed copy of numbers.json. The file itself is never touched."""
        spec = self.numbers()
        if not spec:
            raise NotFound("numbers.json")
        spec = json.loads(json.dumps(spec))
        for field, scale in (("variable", "variable_scale"), ("fixed_monthly", "fixed_scale"), ("startup", "startup_scale")):
            f = float(change.get(scale) or 1.0)
            for it in spec.get(field, []):
                it["cost"] = float(it["cost"]) * f
        if change.get("days_per_month"):
            spec["days_per_month"] = float(change["days_per_month"])
        price = float(change["price"]) if change.get("price") not in (None, "") else None
        volume = float(change.get("volume") or 1.0)
        a = tools.unit_economics().analyse(spec, price=price, volume=volume)
        return tools.clean(a)

    # ── offer ──────────────────────────────────────────────────────────────────
    def offer(self):
        return {"report": self.read("offer.md"), "pitch_now": self.read("pitch.md"), "pitch_v1": self.read("pitch-v1.md")}


def _brief_numbers(a):
    keep = ("price", "contribution", "contribution_pct", "margin_at_plan", "breakeven_per_day",
            "year1_profit", "year1_after_startup", "payback_month", "cash_needed")
    return {k: a.get(k) for k in keep}


def _sections(text):
    """## headings of a markdown file to their body, for the board's side-by-side view."""
    out, cur, buf = {}, None, []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur:
                out[cur] = "\n".join(buf).strip()
            cur, buf = line[3:].strip(), []
        elif cur:
            buf.append(line)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out
