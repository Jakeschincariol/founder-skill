"""Phase 3: the founder's feedback, written where the skills will read it.

One markdown file per step, founder/feedback/<step>.md. The file is the only
copy (no hidden database), so the founder can also edit it by hand and a skill
can tick items off when it acts on them:

    # Feedback: board

    ## Open
    - [ ] change: Score the café on weekday traffic, not weekends. (on board/offers.md: "What would kill it")
    - [ ] keep: The pop-up test first. (on launch.md)

    ## Addressed
    - [x] question: Why only three members? (answered: the pack has three lenses)

Every skill in the pack has a "Founder feedback" section that tells it to read
the open items before it starts and move each one to Addressed with one line on
what it did.
"""

import os
import re

from . import steps

KINDS = ("change", "keep", "question")
ITEM = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(?:(change|keep|question):\s*)?(.+?)\s*$")


def _path(p, step):
    if step not in steps.KEYS:
        raise ValueError("unknown step %r" % step)
    return p.path(os.path.join("feedback", step + ".md"))


def read(p, step):
    path = _path(p, step)
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return {"step": step, "open": [], "addressed": [], "exists": False}
    open_, done, section = [], [], "open"
    for line in text.splitlines():
        h = line.strip().lower()
        if h.startswith("## "):
            section = "addressed" if "address" in h or "done" in h else "open"
            continue
        m = ITEM.match(line)
        if not m:
            continue
        body = m.group(3)
        ref = None
        rm = re.search(r"\s*\(on ([^)]+)\)\s*$", body)
        if rm:
            ref, body = rm.group(1), body[:rm.start()]
        item = {"kind": m.group(2) or "change", "text": body, "ref": ref,
                "checked": m.group(1).lower() == "x"}
        (done if section == "addressed" or item["checked"] else open_).append(item)
    return {"step": step, "open": open_, "addressed": done, "exists": True}


def _write(p, step, open_, done):
    path = _path(p, step)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    def line(it, x):
        ref = " (on %s)" % it["ref"] if it.get("ref") else ""
        return "- [%s] %s: %s%s" % (x, it["kind"], it["text"].replace("\n", " ").strip(), ref)
    L = ["# Feedback: %s" % step, "",
         "Written by the founder in Founder GUI (or by hand). Read the open items before you start;",
         "move each one to Addressed when done, with one line on what you changed.", "",
         "## Open", ""]
    L += [line(it, " ") for it in open_] or ["(nothing open)"]
    L += ["", "## Addressed", ""]
    L += [line(it, "x") for it in done]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L).rstrip() + "\n")


def add(p, step, kind, text, ref=None):
    if kind not in KINDS:
        raise ValueError("kind must be one of %s" % ", ".join(KINDS))
    text = (text or "").strip()
    if not text:
        raise ValueError("empty feedback")
    cur = read(p, step)
    cur["open"].append({"kind": kind, "text": text, "ref": (ref or "").strip() or None})
    _write(p, step, cur["open"], cur["addressed"])
    return read(p, step)


def resolve(p, step, index, reopen=False):
    """Move an item between Open and Addressed by its position in the source list."""
    cur = read(p, step)
    src, dst = (cur["addressed"], cur["open"]) if reopen else (cur["open"], cur["addressed"])
    if not 0 <= index < len(src):
        raise ValueError("no such item")
    dst.append(src.pop(index))
    _write(p, step, cur["open"], cur["addressed"])
    return read(p, step)


def remove(p, step, index, addressed=False):
    cur = read(p, step)
    lst = cur["addressed"] if addressed else cur["open"]
    if not 0 <= index < len(lst):
        raise ValueError("no such item")
    lst.pop(index)
    _write(p, step, cur["open"], cur["addressed"])
    return read(p, step)


def summary(p):
    out = {}
    for k in steps.KEYS:
        f = read(p, k)
        if f["exists"]:
            out[k] = {"open": len(f["open"]), "addressed": len(f["addressed"])}
    return out

