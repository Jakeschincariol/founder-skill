"""Rounds: dated copies of founder/, so round 1 can be set against round 2.

A round is a plain copy of founder/ (the GUI's own folder and the panel's briefs
left out) in founder/.gui/rounds/<id>/, with the key numbers worked out at the
time in meta.json. Running two versions of a pitch is done here, one after the
other, never by pointing two sessions at the same folder.
"""

import difflib
import json
import os
import re
import shutil
import time

from .project import Project

SKIP = ("panel/briefs/",)


def _dir(p):
    return os.path.join(p.gdir, "rounds")


def metrics(p):
    """The numbers worth comparing between rounds, from whatever exists."""
    m = {"verdict": p.verdict()["verdict"]}
    cfo = p.cfo().get("analysis") or {}
    for k in ("price", "contribution", "margin_at_plan", "breakeven_per_day", "year1_profit", "cash_needed", "payback_month"):
        m[k] = cfo.get(k)
    panel = p.panel()
    res = panel.get("results") or panel.get("live") or {}
    m["buy_rate"] = res.get("buy_rate")
    m["buys"] = res.get("buys")
    m["answered"] = res.get("answered")
    pr = p.pricing().get("analysis") or {}
    m["price_range"] = pr.get("range")
    m["opp"] = (pr.get("points") or {}).get("OPP")
    board = p.board()["memos"]
    scores = [b["score"] for b in board if b["score"] is not None]
    m["board_score"] = sum(scores) / len(scores) if scores else None
    m["board_votes"] = [b["vote"] for b in board if b["vote"]]
    return m


def snapshot(p, label=""):
    rid = time.strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", (label or "").lower()).strip("-")[:40]
    if slug:
        rid += "-" + slug
    dest = os.path.join(_dir(p), rid)
    files = p.scan()
    for rel in files:
        if rel.startswith(SKIP):
            continue
        out = os.path.join(dest, "files", rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy2(os.path.join(p.fdir, rel), out)
    meta = {"id": rid, "label": label or rid, "created": time.time(), "metrics": metrics(p),
            "files": sorted(r for r in files if not r.startswith(SKIP))}
    os.makedirs(dest, exist_ok=True)
    with open(os.path.join(dest, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return meta


def listing(p):
    d = _dir(p)
    out = []
    if os.path.isdir(d):
        for rid in sorted(os.listdir(d), reverse=True):
            try:
                with open(os.path.join(d, rid, "meta.json"), encoding="utf-8") as fh:
                    m = json.load(fh)
                m.pop("files", None)
                out.append(m)
            except (OSError, json.JSONDecodeError):
                pass
    return out


def _round_dir(p, rid):
    if not re.match(r"^[\w.-]+$", rid):
        raise ValueError("bad round id")
    d = os.path.join(_dir(p), rid)
    if not os.path.isdir(d):
        raise ValueError("no such round")
    return d


def as_project(p, rid):
    """A read-only Project over a round's copy, so every view can show an old round."""
    rp = Project(os.path.join(_round_dir(p, rid), "files"))
    # files/ is not named founder, so point it at itself
    rp.root, rp.fdir = p.root, os.path.realpath(os.path.join(_round_dir(p, rid), "files"))
    rp.gdir = os.path.join(rp.fdir, ".gui")
    return rp


def read(p, rid, rel):
    return as_project(p, rid).read(rel)


def compare(p, a, b):
    """a and b are round ids, or "current". Returns both metric sets and what changed."""
    def side(rid):
        if rid == "current":
            return {"id": "current", "label": "current", "metrics": metrics(p)}, p
        with open(os.path.join(_round_dir(p, rid), "meta.json"), encoding="utf-8") as fh:
            meta = json.load(fh)
        return meta, as_project(p, rid)

    ma, pa = side(a)
    mb, pb = side(b)
    fa, fb = pa.scan(), pb.scan()
    texts = {}
    for rel in sorted(set(fa) | set(fb)):
        if not rel.endswith(".md") or rel.startswith("panel/"):
            continue
        ta, tb = pa.read(rel) or "", pb.read(rel) or ""
        if ta != tb:
            diff = list(difflib.unified_diff(ta.splitlines(), tb.splitlines(), lineterm="", n=1))
            texts[rel] = {"added": rel not in fa, "removed": rel not in fb, "diff": diff[2:400]}
    ma = dict(ma)
    mb = dict(mb)
    ma.pop("files", None)
    mb.pop("files", None)
    return {"a": ma, "b": mb, "changed": texts}
