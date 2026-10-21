"""The eleven steps of the pack, the files each one writes, and how to tell where a project stands.

A step's status comes only from the files on disk:

    empty     none of its files exist
    partial   some files exist but not the main one
    done      the main file exists
    stale     done, but a file it depends on changed after it ran (re-run it)
    running   one of its files changed in the last few seconds, or a GUI run is active
"""

import os
import time

RUNNING_WINDOW = 20  # seconds since the last write for a step to count as running
STALE_SLACK = 2      # seconds of tolerance, so files a step writes in one go do not look stale

# key, skill, primary output, every output, depends on (a newer file here means re-run)
STEPS = [
    ("board", "founder-board", "board.md",
     ["idea.md", "board.md", "board/"], []),
    ("competitors", "founder-competitors", "competitors.md",
     ["competitors.md", "competitors.csv"], ["idea.md"]),
    ("consumer", "founder-consumer", "panel/results.md",
     ["customer.json", "pitch.md", "panel/"], ["pitch.md", "customer.json"]),
    ("pricing", "founder-pricing", "pricing.md",
     ["pricing.md", "pricing-curve.md"], ["panel/results.json", "competitors.csv"]),
    ("offer", "founder-offer", "offer.md",
     ["offer.md", "pitch-v1.md"], ["panel/results.json", "board.md"]),
    ("cfo", "founder-cfo", "cfo.md",
     ["numbers.json", "cfo.md", "cfo-sources.md"], ["numbers.json", "pricing.md", "offer.md"]),
    ("marketing", "founder-marketing", "marketing.md",
     ["marketing.md"], ["offer.md", "pricing.md", "numbers.json"]),
    ("brand", "founder-brand", "brand.md",
     ["brand.md"], ["marketing.md", "pitch.md"]),
    ("ops", "founder-ops", "ops.md",
     ["ops.md"], ["offer.md"]),
    ("launch", "founder-launch", "launch.md",
     ["launch.md"], ["ops.md", "brand.md", "marketing.md"]),
    ("plan", "founder-plan", "business-plan.md",
     ["business-plan.md", "summary.md", "one-pager.md"],
     ["board.md", "competitors.md", "panel/results.md", "pricing.md", "offer.md", "cfo.md",
      "marketing.md", "brand.md", "ops.md", "launch.md"]),
]

KEYS = [s[0] for s in STEPS]
BY_KEY = {s[0]: s for s in STEPS}


def owner(relpath):
    """The step that writes a file (relative to founder/), or None."""
    for key, _, _, outputs, _ in STEPS:
        for o in outputs:
            if (o.endswith("/") and relpath.startswith(o)) or relpath == o:
                return key
    return None


def _newest(files, pattern):
    """Newest mtime among files matching an output pattern (a file or a folder/)."""
    if pattern.endswith("/"):
        times = [m for p, m in files.items() if p.startswith(pattern)]
        return max(times) if times else None
    return files.get(pattern)


def status(files, active_runs=(), now=None):
    """files: {relpath: mtime}. Returns one dict per step, in pipeline order."""
    now = now or time.time()
    out = []
    for key, skill, primary, outputs, depends in STEPS:
        have = [o for o in outputs if _newest(files, o) is not None]
        last = max([_newest(files, o) for o in have] or [0]) or None
        primary_t = _newest(files, primary)
        stale_by = []
        if primary_t is not None:
            for dep in depends:
                t = files.get(dep)
                if t is not None and t > primary_t + STALE_SLACK and dep != primary:
                    stale_by.append(dep)
        if key in active_runs or (last and now - last < RUNNING_WINDOW):
            st = "running"
        elif primary_t is None:
            st = "partial" if have else "empty"
        elif stale_by:
            st = "stale"
        else:
            st = "done"
        out.append({"key": key, "skill": skill, "primary": primary, "status": st,
                    "files": have, "updated": last, "stale_by": stale_by,
                    "gui_run": key in active_runs})
    return out


def next_step(statuses):
    """The first step that still needs doing, the way the pack runs them."""
    for s in statuses:
        if s["status"] in ("empty", "partial", "stale"):
            return s["key"]
    return None
