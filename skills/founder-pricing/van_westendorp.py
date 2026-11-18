#!/usr/bin/env python3
"""Price sensitivity (Van Westendorp) for founder-pricing. Standard library only.

Every buyer on the panel answers four questions: at what price would it be too
cheap to trust, a bargain, getting expensive, and too expensive to buy. Plotted
together, those four answers give you an acceptable price range and the price
that leaves the fewest people unhappy.

    python3 van_westendorp.py founder/panel/answers
    python3 van_westendorp.py prices.csv --out founder/pricing-curve.md
    python3 van_westendorp.py founder/panel/answers --json

Input is either the panel's answers folder (one JSON per buyer, written by
founder-consumer) or a CSV with the columns too_cheap, cheap, expensive,
too_expensive (one row per respondent; extra columns are ignored; ',' ';' or tab
between columns). Typed prices may use a decimal comma: 12,50 is 12.5, while
1,250 is read as 1250 (--decimal comma reads it as 1.25). A respondent
missing any of the four numbers, or giving them out of order (too cheap must be
the lowest, too expensive the highest), is dropped and counted.

The four points it reports:

    PMC  point of marginal cheapness   below this, too many think it's too cheap
    PME  point of marginal expensiveness above this, too many think it's too expensive
    OPP  optimal price point            as many say "too cheap" as "too expensive"
    IPP  indifference price point       as many say "a bargain" as "expensive"

PMC to PME is the acceptable range. These are answers from simulated buyers:
use the range to choose what to TEST, then test it with real ones.
"""

import argparse
import csv
import glob
import json
import math
import os
import re
import sys

KEYS = ("too_cheap", "cheap", "expensive", "too_expensive")
DECIMALS = ("auto", "point", "comma")


class PricingError(Exception):
    pass


_CURRENCY = re.compile(r"(?i)(us\$|ca\$|au\$|\$|€|£|euros?|eur|usd|cad|gbp|chf|dollars?)")
_SPACING = re.compile(r"[\s  '’]")
_GROUPED = {",": re.compile(r"^\d{1,3}(,\d{3})+$"), ".": re.compile(r"^\d{1,3}(\.\d{3})+$")}


def parse_number(v, decimal="auto"):
    """A number from a JSON value or a typed string, or None when it cannot be read without guessing.

    Reads 12.50, 12,50, 1,250.50, 1.250,50, 1 250,50, $12, 12 EUR. decimal="auto" takes a lone comma
    as the decimal mark ("12,50" is 12.5) unless it groups thousands ("1,250" is 1250); "point" or
    "comma" forces the mark. Kept identical in founder-consumer/panel.py (skills ship alone).
    """
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return x if math.isfinite(x) else None
    if not isinstance(v, str):
        return None
    s = _SPACING.sub("", _CURRENCY.sub("", v))
    sign = -1.0 if s.startswith("-") else 1.0
    s = s.lstrip("-")
    if not s or not re.fullmatch(r"[\d.,]+", s) or not re.search(r"\d", s):
        return None
    if decimal == "point":
        dec = "."
    elif decimal == "comma":
        dec = ","
    elif "," in s and "." in s:
        dec = "," if s.rfind(",") > s.rfind(".") else "."
    elif "," in s:
        dec = "." if _GROUPED[","].match(s) else ","
    elif s.count(".") > 1:
        dec = "," if _GROUPED["."].match(s) else "."
    else:
        dec = "."
    sep = "," if dec == "." else "."
    whole, frac = (s.rsplit(dec, 1) + [""])[:2] if dec in s else (s, "")
    if dec in whole or sep in frac:
        return None
    if sep in whole:
        if not _GROUPED[sep].match(whole):
            return None
        whole = whole.replace(sep, "")
    return sign * float("%s.%s" % (whole or "0", frac or "0"))


def _f(v, decimal="auto"):
    x = parse_number(v, decimal)
    return x if x is not None and x > 0 else None


def _csv_delimiter(fh):
    """Excel in Europe writes ';' between columns because ',' is the decimal mark.
    Decided from the header line only: it holds column names, never a decimal number."""
    header = fh.readline()
    fh.seek(0)
    counts = {d: header.count(d) for d in (",", ";", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] else ","


def read(path, decimal="auto"):
    """Return (rows, dropped) where rows are (too_cheap, cheap, expensive, too_expensive)."""
    if decimal not in DECIMALS:
        raise PricingError("decimal must be one of %s" % ", ".join(DECIMALS))
    raw = []
    if os.path.isdir(path):
        for fp in sorted(glob.glob(os.path.join(path, "*.json"))):
            try:
                with open(fp, encoding="utf-8") as fh:
                    a = json.load(fh)
            except (json.JSONDecodeError, UnicodeDecodeError):
                raw.append(None)
                continue
            if not isinstance(a, dict):
                raw.append(None)
                continue
            raw.append(tuple(_f(a.get("price_" + k), decimal) for k in KEYS))
    elif path.endswith(".csv"):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh, delimiter=_csv_delimiter(fh)):
                raw.append(tuple(_f(r.get(k), decimal) for k in KEYS))
    else:
        raise PricingError("give the panel's answers folder or a .csv")
    rows, dropped = [], 0
    for r in raw:
        if r is None or any(v is None for v in r) or not (r[0] <= r[1] <= r[2] <= r[3]):
            dropped += 1
            continue
        rows.append(r)
    return rows, dropped


def curves(rows, grid):
    n = float(len(rows))
    tc = [sum(1 for r in rows if r[0] >= p) / n for p in grid]          # too cheap at p (falls)
    ch = [sum(1 for r in rows if r[1] >= p) / n for p in grid]          # a bargain at p (falls)
    ex = [sum(1 for r in rows if r[2] <= p) / n for p in grid]          # expensive at p (rises)
    te = [sum(1 for r in rows if r[3] <= p) / n for p in grid]          # too expensive at p (rises)
    return tc, ch, ex, te


def cross(grid, falling, rising):
    """First price where the rising curve meets the falling one (linear interpolation)."""
    for i in range(1, len(grid)):
        d0 = rising[i - 1] - falling[i - 1]
        d1 = rising[i] - falling[i]
        if d0 <= 0 <= d1 and d1 != d0:
            t = -d0 / (d1 - d0)
            return grid[i - 1] + t * (grid[i] - grid[i - 1])
        if d0 == 0:
            return grid[i - 1]
    return None


def analyse(rows, step=None):
    if len(rows) < 5:
        raise PricingError("need at least 5 complete answers (got %d)" % len(rows))
    lo = min(r[0] for r in rows)
    hi = max(r[3] for r in rows)
    step = step or max(0.01, round((hi - lo) / 400, 2))
    grid, p = [], lo
    while p <= hi + 1e-9:
        grid.append(round(p, 4))
        p += step
    tc, ch, ex, te = curves(rows, grid)
    not_cheap = [1 - v for v in ch]
    not_exp = [1 - v for v in ex]
    pts = {
        "PMC": cross(grid, tc, not_cheap),
        "PME": cross(grid, not_exp, te),
        "OPP": cross(grid, tc, te),
        "IPP": cross(grid, ch, ex),
    }
    return {"n": len(rows), "points": pts, "range": [pts["PMC"], pts["PME"]],
            "median": {k: sorted(r[i] for r in rows)[len(rows) // 2] for i, k in enumerate(KEYS)}}


def report(res, dropped, price=None):
    m = lambda v: "n/a" if v is None else "$%.2f" % v
    p = res["points"]
    L = ["# Price sensitivity", "",
         "%d complete answers%s. Simulated buyers: use this to pick what to test, not as the final word." % (
             res["n"], (", %d dropped (incomplete or out of order)" % dropped) if dropped else ""), "",
         "| point | price | what it means |", "| --- | ---: | --- |",
         "| PMC | %s | below this, too many think it is too cheap to be good |" % m(p["PMC"]),
         "| OPP | %s | as many say too cheap as too expensive: the least resistance |" % m(p["OPP"]),
         "| IPP | %s | as many call it a bargain as call it expensive |" % m(p["IPP"]),
         "| PME | %s | above this, too many say it is too expensive to buy |" % m(p["PME"]), "",
         "**Acceptable range: %s to %s.**" % (m(p["PMC"]), m(p["PME"])), ""]
    md = res["median"]
    L.append("Median answers: too cheap %s, a bargain %s, getting expensive %s, too expensive %s." % (
        m(md["too_cheap"]), m(md["cheap"]), m(md["expensive"]), m(md["too_expensive"])))
    if price is not None and p["PMC"] is not None and p["PME"] is not None:
        where = "inside" if p["PMC"] <= price <= p["PME"] else ("below" if price < p["PMC"] else "above")
        L += ["", "Your current price, %s, is **%s** the acceptable range." % (m(price), where)]
    return "\n".join(L) + "\n"


def _price_arg(text):
    x = parse_number(text)
    if x is None or x <= 0:
        raise argparse.ArgumentTypeError("not a price: %r" % text)
    return x


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source", help="the panel's answers folder, or a CSV")
    ap.add_argument("--price", type=_price_arg, help="your current price, to place it on the range (6.50 or 6,50)")
    ap.add_argument("--decimal", choices=DECIMALS, default="auto",
                    help="decimal mark in typed answers: auto (12,50 is 12.5; 1,250 is 1250), point, or comma")
    ap.add_argument("--out", help="write the report here (markdown)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        rows, dropped = read(a.source, a.decimal)
        res = analyse(rows)
    except (PricingError, FileNotFoundError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(dict(res, dropped=dropped), indent=1))
        return 0
    text = report(res, dropped, a.price)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s" % a.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
