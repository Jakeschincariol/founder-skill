"""Which Claude Code sessions are open in a project folder.

The skills do not lock anything: two sessions running the same step in the same
folder overwrite each other's files. The GUI cannot stop a terminal session, but
it can see one and warn before it starts a run of its own.

Uses lsof (macOS and most Linux). Without it, the list is simply empty.
"""

import os
import shutil
import subprocess
import time

_cache = {"at": 0, "rows": []}
CACHE_SECONDS = 3


def claude_processes():
    """[(pid, cwd)] for every process named claude. Cached for a few seconds."""
    now = time.time()
    if now - _cache["at"] < CACHE_SECONDS:
        return _cache["rows"]
    rows = []
    if shutil.which("lsof"):
        try:
            out = subprocess.run(["lsof", "-a", "-c", "claude", "-d", "cwd", "-Fpn"],
                                 capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.SubprocessError):
            out = ""
        pid = None
        for line in out.splitlines():
            if line.startswith("p"):
                pid = int(line[1:])
            elif line.startswith("n") and pid is not None:
                rows.append((pid, os.path.realpath(line[1:])))
    _cache.update(at=now, rows=rows)
    return rows


def in_folder(root, exclude_pids=()):
    """Claude sessions whose working folder is the project folder or inside it."""
    root = os.path.realpath(root)
    return [{"pid": pid, "cwd": cwd} for pid, cwd in claude_processes()
            if pid not in exclude_pids and pid != os.getpid()
            and (cwd == root or cwd.startswith(root + os.sep))]
