"""The HTTP side: a JSON API over the projects, server-sent events, and the static page.

Bound to 127.0.0.1. Two guards, because this server can start Claude sessions:
- the Host header must be localhost or 127.0.0.1 (stops DNS rebinding);
- every write needs the X-Founder-GUI header, which a page on another site
  cannot send without a CORS preflight this server never answers.
"""

import json
import mimetypes
import os
import queue
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from . import VERSION, export, feedback, registry, rounds, runs, sessions, steps, tools
from .project import NotFound
from .watch import Bus, Watcher

STATIC = os.path.join(tools.GUI_DIR, "static")
HEADER = "X-Founder-GUI"


class App:
    def __init__(self):
        self.bus = Bus()
        self.runs = runs.Manager(self.bus)
        self.watcher = Watcher(self.bus)

    def project(self, pid, query=None):
        p = registry.get(pid)
        if p is None:
            raise NotFound("project " + pid)
        rid = (query or {}).get("round", [None])[0]
        return rounds.as_project(p, rid) if rid else p

    def summary(self, p):
        st = p.state(self.runs.active_steps(p))
        done = sum(1 for s in st["steps"] if s["status"] in ("done", "stale"))
        return {"id": p.id, "name": st["name"], "root": p.root, "founder_dir": p.fdir, "exists": st["exists"],
                "done": done, "total": len(st["steps"]), "verdict": st["verdict"]["verdict"],
                "updated": st["updated"], "next": st["next"],
                "running": [s["key"] for s in st["steps"] if s["status"] == "running"],
                "sessions": len(sessions.in_folder(p.root, self.runs.our_pids())),
                "gui_run": self.runs.active(p)}


def make_handler(app):
    class H(BaseHTTPRequestHandler):
        server_version = "FounderGUI/" + VERSION
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # quiet: the terminal is not the place for access logs
            pass

        # ── plumbing ───────────────────────────────────────────────────────────
        def _host_ok(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
            return host in ("localhost", "127.0.0.1", "::1")

        def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
            if not isinstance(body, (bytes, bytearray)):
                body = json.dumps(body, allow_nan=False).encode("utf-8") if "json" in ctype else str(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json_body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > 2_000_000:
                raise ValueError("body too large")
            raw = self.rfile.read(n) if n else b""
            return json.loads(raw.decode("utf-8")) if raw else {}

        def _route(self, method):
            if not self._host_ok():
                return self._send(403, {"error": "bad host"})
            if method != "GET" and self.headers.get(HEADER) != "1":
                return self._send(403, {"error": "missing %s header" % HEADER})
            u = urlparse(self.path)
            path, q = unquote(u.path), parse_qs(u.query)
            try:
                if method == "GET" and path == "/api/events":
                    return self._events()
                if not path.startswith("/api/"):
                    return self._static(path) if method == "GET" else self._send(404, {"error": "not found"})
                body = self._json_body() if method in ("POST", "PUT") else {}
                res = dispatch(app, method, path, q, body)
                if isinstance(res, tuple) and res and res[0] == "raw":
                    _, ctype, data, extra = res
                    return self._send(200, data, ctype, extra)
                return self._send(200, res)
            except NotFound as e:
                return self._send(404, {"error": "not found: %s" % e})
            except runs.Busy as e:
                return self._send(409, {"error": str(e), "sessions": e.sessions, "run": e.run})
            except (ValueError, KeyError, runs.RunError) as e:
                return self._send(400, {"error": str(e)})
            except Exception as e:  # report, do not crash the hub
                return self._send(500, {"error": "%s: %s" % (type(e).__name__, e)})

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

        def do_DELETE(self):
            self._route("DELETE")

        def _static(self, path):
            rel = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
            if rel.startswith("static/"):
                rel = rel[len("static/"):]
            full = os.path.realpath(os.path.join(STATIC, rel))
            if not full.startswith(os.path.realpath(STATIC) + os.sep) or not os.path.isfile(full):
                return self._send(404, {"error": "not found"})
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript",):
                ctype += "; charset=utf-8"
            with open(full, "rb") as fh:
                self._send(200, fh.read(), ctype)

        def _events(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            q = app.bus.subscribe()
            try:
                self.wfile.write(b"retry: 2000\n\n")
                self.wfile.flush()
                while True:
                    try:
                        msg = q.get(timeout=15)
                        self.wfile.write(("data: %s\n\n" % msg).encode("utf-8"))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                app.bus.unsubscribe(q)
                self.close_connection = True

    return H


ROUTES = []


def route(method, pattern):
    def deco(fn):
        ROUTES.append((method, re.compile("^" + pattern + "$"), fn))
        return fn
    return deco


def dispatch(app, method, path, q, body):
    for m, rx, fn in ROUTES:
        if m == method:
            mt = rx.match(path)
            if mt:
                return fn(app, q, body, *mt.groups())
    raise NotFound(path)


# ── hub ────────────────────────────────────────────────────────────────────────
@route("GET", r"/api/ping")
def _ping(app, q, body):
    return {"app": "founder-gui", "version": VERSION, "pid": os.getpid()}


@route("GET", r"/api/projects")
def _projects(app, q, body):
    return [app.summary(p) for p in registry.projects()]


@route("POST", r"/api/projects")
def _add_project(app, q, body):
    if not body.get("path"):
        raise ValueError("path is required")
    p = registry.add(body["path"])
    return app.summary(p)


@route("DELETE", r"/api/projects/(\w+)")
def _remove_project(app, q, body, pid):
    registry.remove(pid)  # forgets the project; its files stay where they are
    return {"ok": True}


# ── one project ────────────────────────────────────────────────────────────────
@route("GET", r"/api/p/(\w+)/state")
def _state(app, q, body, pid):
    p = app.project(pid, q)
    base = registry.get(pid)
    st = p.state(app.runs.active_steps(base))
    st["sessions"] = sessions.in_folder(base.root, app.runs.our_pids())
    st["gui_run"] = app.runs.active(base)
    st["feedback"] = feedback.summary(base)
    st["round"] = q.get("round", [None])[0]
    return tools.clean(st)


@route("GET", r"/api/p/(\w+)/file")
def _file(app, q, body, pid):
    p = app.project(pid, q)
    rel = q.get("path", [""])[0]
    text = p.read(rel)
    if text is None:
        raise NotFound(rel)
    return {"path": rel, "text": text, "mtime": os.path.getmtime(p.path(rel))}


for _view in ("board", "competitors", "panel", "pricing", "cfo", "offer"):
    def _make(view):
        def fn(app, q, body, pid):
            return getattr(app.project(pid, q), view)()
        return fn
    route("GET", r"/api/p/(\w+)/" + _view)(_make(_view))


@route("GET", r"/api/p/(\w+)/panel/brief/(P\d+)")
def _brief(app, q, body, pid, buyer):
    text = app.project(pid, q).brief(buyer)
    if text is None:
        raise NotFound(buyer)
    return {"id": buyer, "text": text}


@route("POST", r"/api/p/(\w+)/cfo/whatif")
def _whatif(app, q, body, pid):
    return app.project(pid).whatif(body)


@route("POST", r"/api/p/(\w+)/checklist")
def _tick(app, q, body, pid):
    p = app.project(pid)
    p.tick(body["id"], body.get("done"), body.get("note", ""))
    return p.checklist()


# ── phase 2: rounds and export ─────────────────────────────────────────────────
@route("GET", r"/api/p/(\w+)/rounds")
def _rounds(app, q, body, pid):
    return rounds.listing(app.project(pid))


@route("POST", r"/api/p/(\w+)/rounds")
def _snapshot(app, q, body, pid):
    return rounds.snapshot(app.project(pid), body.get("label", ""))


@route("GET", r"/api/p/(\w+)/rounds/compare")
def _compare(app, q, body, pid):
    return tools.clean(rounds.compare(app.project(pid), q.get("a", ["current"])[0], q.get("b", ["current"])[0]))


@route("GET", r"/api/p/(\w+)/export")
def _export(app, q, body, pid):
    p = app.project(pid)
    html = export.build(app, p)
    name = re.sub(r"[^A-Za-z0-9]+", "-", p.name()).strip("-").lower() or "founder"
    return ("raw", "text/html; charset=utf-8", html.encode("utf-8"),
            {"Content-Disposition": 'attachment; filename="%s-report-%s.html"' % (name, time.strftime("%Y%m%d"))})


# ── phase 3: feedback ──────────────────────────────────────────────────────────
@route("GET", r"/api/p/(\w+)/feedback")
def _feedback_all(app, q, body, pid):
    p = app.project(pid)
    return {k: feedback.read(p, k) for k in steps.KEYS}


@route("POST", r"/api/p/(\w+)/feedback/(\w+)")
def _feedback(app, q, body, pid, step):
    p = app.project(pid)
    action = body.get("action", "add")
    if action == "add":
        return feedback.add(p, step, body.get("kind", "change"), body.get("text"), body.get("ref"))
    if action in ("resolve", "reopen"):
        return feedback.resolve(p, step, int(body["index"]), reopen=action == "reopen")
    if action == "remove":
        return feedback.remove(p, step, int(body["index"]), addressed=bool(body.get("addressed")))
    raise ValueError("unknown action %r" % action)


# ── phase 4: runs ──────────────────────────────────────────────────────────────
@route("GET", r"/api/p/(\w+)/runs")
def _runs(app, q, body, pid):
    p = app.project(pid)
    return {"runs": app.runs.listing(p), "check": app.runs.check(p),
            "defaults": {"allowed": runs.DEFAULT_TOOLS, "modes": list(runs.MODES)}}


@route("POST", r"/api/p/(\w+)/runs")
def _start(app, q, body, pid):
    return app.runs.start(app.project(pid), body.get("step"), body.get("extra", ""), body.get("mode", "acceptEdits"),
                          body.get("allow") or [], body.get("use_local_skills", True), bool(body.get("force")))


@route("GET", r"/api/p/(\w+)/runs/([\w-]+)")
def _run(app, q, body, pid, rid):
    r = app.runs.get(app.project(pid), rid)
    if r is None:
        raise NotFound(rid)
    return {"run": r.meta, "events": r.events()}


@route("POST", r"/api/p/(\w+)/runs/([\w-]+)/reply")
def _reply(app, q, body, pid, rid):
    return app.runs.reply(app.project(pid), rid, body.get("message", ""), body.get("allow") or [])


@route("POST", r"/api/p/(\w+)/runs/([\w-]+)/cancel")
def _cancel(app, q, body, pid, rid):
    return app.runs.cancel(app.project(pid), rid)


def serve(port=8765, host="127.0.0.1"):
    app = App()
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    httpd.daemon_threads = True
    app.watcher.start()
    return app, httpd
