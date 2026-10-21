"""Phase 2: export a project as one self-contained HTML file to share.

The export is the same page the GUI serves, with its CSS and scripts inlined and
every API answer the page would ask for frozen into window.__FOUNDER_SNAPSHOT__.
It opens anywhere, offline, read-only: no what-if, no feedback, no runs.
"""

import json
import os
import re
import time
from urllib.parse import parse_qs, urlparse

from . import tools

STATIC = os.path.join(tools.GUI_DIR, "static")


def _get(app, url):
    from .server import dispatch  # late import: server imports this module
    u = urlparse(url)
    return dispatch(app, "GET", u.path, parse_qs(u.query), {})


def snapshot(app, p):
    base = "/api/p/%s" % p.id
    data = {"/api/projects": [app.summary(p)]}
    for view in ("state", "board", "competitors", "panel", "pricing", "cfo", "offer", "rounds", "feedback"):
        try:
            data["%s/%s" % (base, view)] = _get(app, "%s/%s" % (base, view))
        except Exception:
            pass
    state = data.get(base + "/state") or {}
    for rel in (d["path"] for d in state.get("docs", [])):
        try:
            data["%s/file?path=%s" % (base, rel)] = _get(app, "%s/file?path=%s" % (base, rel))
        except Exception:
            pass
    return tools.clean(data)


def _inline(html):
    def css(m):
        with open(os.path.join(STATIC, m.group(1)), encoding="utf-8") as fh:
            return "<style>\n%s\n</style>" % fh.read()

    def js(m):
        with open(os.path.join(STATIC, m.group(1)), encoding="utf-8") as fh:
            return "<script>\n%s\n</script>" % fh.read().replace("</script", "<\\/script")

    html = re.sub(r'<link rel="stylesheet" href="/static/([\w.-]+)">', css, html)
    return re.sub(r'<script src="/static/([\w.-]+)"></script>', js, html)


def build(app, p):
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as fh:
        html = fh.read()
    snap = json.dumps({"project": p.id, "exported": time.time(), "data": snapshot(app, p)}, allow_nan=False)
    snap = snap.replace("</", "<\\/")
    html = html.replace("<!--SNAPSHOT-->", "<script>window.__FOUNDER_SNAPSHOT__ = %s;</script>" % snap)
    return _inline(html)
