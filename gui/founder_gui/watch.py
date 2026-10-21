"""Watch every registered founder/ folder and push changes to the browser.

Polling, once a second, because the standard library has no file events. A
founder/ folder holds a few hundred small files at most, so this is cheap.
"""

import json
import queue
import threading
import time

from . import registry, steps


class Bus:
    """Fan-out of events to every open browser tab (one queue per SSE connection)."""

    def __init__(self):
        self._subs = set()
        self._lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue(maxsize=1000)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q):
        with self._lock:
            self._subs.discard(q)

    def publish(self, kind, data):
        msg = json.dumps({"kind": kind, "data": data, "at": time.time()})
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass


class Watcher(threading.Thread):
    def __init__(self, bus, interval=1.0):
        super().__init__(daemon=True)
        self.bus = bus
        self.interval = interval
        self._seen = {}  # project id -> {relpath: mtime}
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:  # never let one bad folder stop the watcher
                pass
            self._stop.wait(self.interval)

    def tick(self):
        for p in registry.projects():
            now = p.scan()
            before = self._seen.get(p.id)
            self._seen[p.id] = now
            if before is None:
                continue
            changed = sorted(k for k, v in now.items() if before.get(k) != v)
            removed = sorted(k for k in before if k not in now)
            if changed or removed:
                touched = sorted({s for s in (steps.owner(f) for f in changed + removed) if s})
                self.bus.publish("files", {"project": p.id, "changed": changed[:200],
                                           "removed": removed[:200], "steps": touched,
                                           "count": len(changed) + len(removed)})
