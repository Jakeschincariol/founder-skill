"""The hub's list of projects, shared by every /founder-gui call on this machine.

One GUI server (the hub) serves every project. The first /founder-gui starts it;
later ones, from other folders or sessions, find it through hub.json and only
register their folder. State lives in ~/.founder-gui (FOUNDER_GUI_HOME overrides).
"""

import json
import os
import threading
import time

from .project import Project

_lock = threading.Lock()


def home():
    d = os.environ.get("FOUNDER_GUI_HOME") or os.path.join(os.path.expanduser("~"), ".founder-gui")
    os.makedirs(d, exist_ok=True)
    return d


def _path():
    return os.path.join(home(), "projects.json")


def _load():
    try:
        with open(_path(), encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save(items):
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=2)
    os.replace(tmp, _path())


def projects():
    with _lock:
        return [Project(it["path"]) for it in _load()]


def add(path):
    p = Project(path)
    with _lock:
        items = _load()
        if not any(Project(it["path"]).id == p.id for it in items):
            items.append({"path": p.fdir, "added": time.time()})
            _save(items)
    return p


def remove(pid):
    with _lock:
        items = [it for it in _load() if Project(it["path"]).id != pid]
        _save(items)


def get(pid):
    for p in projects():
        if p.id == pid:
            return p
    return None


# ── the hub itself ─────────────────────────────────────────────────────────────
def hub_file():
    return os.path.join(home(), "hub.json")


def write_hub(port, pid):
    with open(hub_file(), "w", encoding="utf-8") as fh:
        json.dump({"port": port, "pid": pid, "started": time.time()}, fh)


def read_hub():
    try:
        with open(hub_file(), encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def clear_hub(pid):
    h = read_hub()
    if h and h.get("pid") == pid:
        try:
            os.remove(hub_file())
        except OSError:
            pass
