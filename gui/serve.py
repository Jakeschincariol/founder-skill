#!/usr/bin/env python3
"""Founder GUI: watch the founder/ folder in a browser while the skills run.

    python3 gui/serve.py                      # this folder's founder/, opens the browser
    python3 gui/serve.py --dir path/to/project
    python3 gui/serve.py --detach             # start the hub in the background and return
    python3 gui/serve.py --list               # the projects the hub knows

One hub serves every project on this machine. If it is already running (from
another folder or another Claude session), this only registers the folder with
it and opens the page. Standard library only; the server listens on 127.0.0.1.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from founder_gui import registry, server  # noqa: E402
from founder_gui.project import Project  # noqa: E402

DEFAULT_PORT = 8765


def _call(port, method, path, body=None, timeout=2):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), method=method,
                                 data=json.dumps(body).encode("utf-8") if body is not None else None,
                                 headers={"Content-Type": "application/json", server.HEADER: "1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def running_hub():
    """The port of a live hub, or None."""
    h = registry.read_hub()
    if not h:
        return None
    try:
        if _call(h["port"], "GET", "/api/ping").get("app") == "founder-gui":
            return h["port"]
    except Exception:
        pass
    return None


def _open(port, pid, no_open):
    url = "http://127.0.0.1:%d/#/p/%s" % (port, pid)
    print("Founder GUI: %s" % url)
    if not no_open:
        webbrowser.open(url)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", default=".", help="the project folder, or its founder/ folder (default: here)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    ap.add_argument("--detach", action="store_true", help="run the hub in the background")
    ap.add_argument("--list", action="store_true", help="list registered projects and exit")
    a = ap.parse_args(argv)

    if a.list:
        for p in registry.projects():
            print("%s  %s  %s" % (p.id, p.name(), p.fdir))
        return 0

    p = Project(a.dir.strip() or ".")
    port = running_hub()
    if port:
        info = _call(port, "POST", "/api/projects", {"path": p.fdir})
        print("hub already running on port %d; added %s" % (port, info["name"]))
        _open(port, p.id, a.no_open)
        return 0

    if a.detach:
        log = open(os.path.join(registry.home(), "hub.log"), "a")
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "--dir", p.fdir, "--port", str(a.port), "--no-open"],
                         stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
        for _ in range(50):
            time.sleep(0.1)
            port = running_hub()
            if port:
                _open(port, p.id, a.no_open)
                return 0
        print("the hub did not start; see %s" % os.path.join(registry.home(), "hub.log"), file=sys.stderr)
        return 1

    registry.add(p.fdir)
    httpd = None
    for port in range(a.port, a.port + 20):
        try:
            app, httpd = server.serve(port)
            break
        except OSError:
            continue
    if httpd is None:
        print("no free port from %d to %d" % (a.port, a.port + 19), file=sys.stderr)
        return 1
    registry.write_hub(port, os.getpid())
    if not p.exists():
        print("note: %s does not exist yet; it will show up as soon as a skill writes to it" % p.fdir)
    _open(port, p.id, a.no_open)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        registry.clear_hub(os.getpid())
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
