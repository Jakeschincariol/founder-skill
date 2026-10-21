"""Phase 4: run a step from the browser with `claude -p`, and keep talking to it.

A run is one Claude Code session started in the project folder:

    claude -p "/founder-skill:founder-<step> <extra>" --output-format stream-json --verbose
           --plugin-dir <this repo> --permission-mode acceptEdits --permission-prompts none
           --allowedTools <the tools the pack needs>

Headless sessions cannot ask questions or wait for a permission prompt, so:

- the appended system prompt tells the skill to stop and list its questions in its
  last message instead of guessing; the founder answers in the GUI and the answer
  goes back with `--resume <session id>` (a new turn of the same run);
- anything that would have prompted is denied (`--permission-prompts none`) and
  the denials come back in the result; the GUI offers "allow and continue",
  which resumes with that tool added to --allowedTools.

One GUI run per project at a time (founder/.gui/run.lock). A Claude session
already open in the folder from a terminal is reported, and the founder has to
confirm before the GUI starts another one next to it.
"""

import json
import os
import shutil
import signal
import subprocess
import threading
import time
import uuid

from . import sessions, steps, tools

DEFAULT_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Agent", "Task", "TodoWrite",
                 "WebSearch", "WebFetch", "Bash(python3:*)", "Bash(python:*)", "Bash(mkdir:*)",
                 "Bash(ls:*)", "Bash(cat:*)", "Bash(cp:*)"]
MODES = ("acceptEdits", "auto", "plan")

HEADLESS = """You are running from Founder GUI, in non-interactive mode: the founder watches your output in a browser and cannot answer you mid-run.
- Do not use AskUserQuestion. If you need something only the founder knows (a name, a price, a budget), do not invent it: do every part you can, then end your final message with a section "## Questions for the founder", one numbered question per line. The founder's answers arrive as your next message.
- Before you start, read founder/feedback/{step}.md if it exists and act on every open item, as the skill's "Founder feedback" section says.
- End with a short summary of the files you wrote."""


class RunError(Exception):
    pass


class Busy(RunError):
    def __init__(self, msg, sessions_=None, run=None):
        super().__init__(msg)
        self.sessions = sessions_ or []
        self.run = run


def claude_bin():
    return os.environ.get("FOUNDER_GUI_CLAUDE") or shutil.which("claude")


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, TypeError):
        return False


def simplify(e):
    """One stream-json event to the few kinds the GUI shows, or None to skip it."""
    t = e.get("type")
    sub = bool(e.get("parent_tool_use_id"))
    if t == "system" and e.get("subtype") == "init":
        return [{"t": "init", "session": e.get("session_id"), "model": e.get("model"),
                 "mode": e.get("permissionMode")}]
    if t in ("assistant", "user"):
        msg = e.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        out = []
        for c in content or []:
            ct = c.get("type")
            if ct == "text" and t == "assistant" and c.get("text", "").strip():
                out.append({"t": "text", "text": c["text"], "sub": sub})
            elif ct == "tool_use":
                out.append({"t": "tool", "id": c.get("id"), "name": c.get("name"),
                            "input": _short_input(c.get("input")), "sub": sub})
            elif ct == "tool_result":
                body = c.get("content")
                if isinstance(body, list):
                    body = "\n".join(x.get("text", "") for x in body if isinstance(x, dict))
                out.append({"t": "result", "id": c.get("tool_use_id"), "text": str(body or "")[:3000],
                            "error": bool(c.get("is_error")), "sub": sub})
        return out or None
    if t == "result":
        return [{"t": "done", "ok": e.get("subtype") == "success" and not e.get("is_error"),
                 "text": e.get("result", ""), "cost": e.get("total_cost_usd"),
                 "turns": e.get("num_turns"), "session": e.get("session_id"),
                 "denials": [{"tool": d.get("tool_name"), "input": _short_input(d.get("tool_input"))}
                             for d in (e.get("permission_denials") or [])]}]
    return None


def _short_input(inp):
    if not isinstance(inp, dict):
        return inp
    out = {}
    for k, v in inp.items():
        s = v if isinstance(v, (int, float, bool)) or v is None else str(v)
        out[k] = s[:600] + "..." if isinstance(s, str) and len(s) > 600 else s
    return out


def denial_rule(d):
    """A denied tool call to the --allowedTools rule that would have let it through."""
    tool = d.get("tool") or ""
    if tool == "Bash":
        cmd = str((d.get("input") or {}).get("command", "")).strip().split()
        return "Bash(%s:*)" % cmd[0] if cmd else "Bash"
    return tool


class Run:
    def __init__(self, project, step, meta=None):
        self.project = project
        self.dir = os.path.join(project.gdir, "runs")
        if meta:
            self.meta = meta
        else:
            self.meta = {"id": time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4], "step": step,
                         "project": project.id, "status": "starting", "session": None, "created": time.time(),
                         "turns": [], "allowed": list(DEFAULT_TOOLS), "mode": "acceptEdits",
                         "use_local_skills": True, "cost": 0.0}
        self.proc = None

    @property
    def id(self):
        return self.meta["id"]

    def _save(self):
        os.makedirs(self.dir, exist_ok=True)
        tmp = os.path.join(self.dir, self.id + ".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.meta, fh, indent=2)
        os.replace(tmp, os.path.join(self.dir, self.id + ".json"))

    def log(self, ev):
        os.makedirs(self.dir, exist_ok=True)
        ev = dict(ev, at=time.time(), turn=len(self.meta["turns"]))
        with open(os.path.join(self.dir, self.id + ".jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev) + "\n")
        return ev

    def events(self):
        path = os.path.join(self.dir, self.id + ".jsonl")
        out = []
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except FileNotFoundError:
            pass
        return out


class Manager:
    def __init__(self, bus):
        self.bus = bus
        self.live = {}  # run id -> Run with a process
        self._lock = threading.Lock()

    # ── locks ──────────────────────────────────────────────────────────────────
    def _lock_path(self, p):
        return os.path.join(p.gdir, "run.lock")

    def active(self, p):
        """The GUI run holding this project's lock, or None (a lock left by a dead process is cleared)."""
        try:
            with open(self._lock_path(p), encoding="utf-8") as fh:
                lk = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        if lk.get("run") in self.live or _pid_alive(lk.get("pid")):
            return lk
        try:
            os.remove(self._lock_path(p))
        except OSError:
            pass
        return None

    def active_steps(self, p):
        lk = self.active(p)
        return {lk["step"]} if lk else set()

    def our_pids(self):
        return {r.proc.pid for r in self.live.values() if r.proc}

    def check(self, p):
        """What stands in the way of a run: the GUI lock, and Claude sessions open in the folder."""
        return {"lock": self.active(p), "sessions": sessions.in_folder(p.root, self.our_pids()),
                "claude": bool(claude_bin())}

    # ── runs ───────────────────────────────────────────────────────────────────
    def start(self, p, step, extra="", mode="acceptEdits", allow=(), use_local_skills=True, force=False):
        if step not in steps.KEYS:
            raise RunError("unknown step %r" % step)
        if mode not in MODES:
            raise RunError("mode must be one of %s" % ", ".join(MODES))
        if not claude_bin():
            raise RunError("the claude command is not on PATH")
        os.makedirs(p.fdir, exist_ok=True)
        with self._lock:
            lk = self.active(p)
            if lk:
                raise Busy("step %s is already running from the GUI" % lk["step"], run=lk)
            others = sessions.in_folder(p.root, self.our_pids())
            if others and not force:
                raise Busy("%d Claude session(s) already open in this folder" % len(others), sessions_=others)
            run = Run(p, step)
            run.meta.update(mode=mode, use_local_skills=bool(use_local_skills),
                            allowed=list(dict.fromkeys(list(DEFAULT_TOOLS) + [a for a in allow if a])))
            skill = steps.BY_KEY[step][1]
            prompt = ("/founder-skill:%s %s" % (skill, extra or "")).strip()
            self._spawn(p, run, prompt, resume=False)
            return run.meta

    def reply(self, p, rid, message, allow=()):
        run = self.get(p, rid)
        if run is None:
            raise RunError("no such run")
        if run.id in self.live:
            raise Busy("this run is still working")
        if not run.meta.get("session"):
            raise RunError("this run has no session to continue")
        with self._lock:
            lk = self.active(p)
            if lk:
                raise Busy("step %s is already running from the GUI" % lk["step"], run=lk)
            run.meta["allowed"] = list(dict.fromkeys(run.meta["allowed"] + [a for a in allow if a]))
            self._spawn(p, run, message.strip() or "Continue.", resume=True)
            return run.meta

    def cancel(self, p, rid):
        run = self.live.get(rid)
        if not run or not run.proc:
            raise RunError("this run is not working")
        try:
            os.killpg(run.proc.pid, signal.SIGTERM)
        except OSError:
            run.proc.terminate()
        run.meta["status"] = "cancelled"
        return run.meta

    def _spawn(self, p, run, prompt, resume):
        m = run.meta
        cmd = [claude_bin(), "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--permission-mode", m["mode"], "--permission-prompts", "none",
               "--append-system-prompt", HEADLESS.format(step=m["step"]),
               "--allowedTools"] + m["allowed"]
        if m.get("use_local_skills"):
            cmd += ["--plugin-dir", tools.REPO_ROOT]
        if resume:
            cmd += ["--resume", m["session"]]
        m["turns"].append({"prompt": prompt, "started": time.time(), "ended": None, "ok": None})
        m["status"] = "running"
        run.log({"t": "prompt", "text": prompt})
        env = dict(os.environ, FOUNDER_GUI_RUN=run.id)
        run.proc = subprocess.Popen(cmd, cwd=p.root, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, bufsize=1, env=env,
                                    start_new_session=True)
        os.makedirs(p.gdir, exist_ok=True)
        with open(self._lock_path(p), "w", encoding="utf-8") as fh:
            json.dump({"run": run.id, "step": m["step"], "pid": run.proc.pid, "since": time.time()}, fh)
        run._save()
        self.live[run.id] = run
        self.bus.publish("run", {"project": p.id, "run": run.meta})
        threading.Thread(target=self._pump, args=(p, run), daemon=True).start()
        threading.Thread(target=self._pump_err, args=(p, run), daemon=True).start()

    def _emit(self, p, run, ev):
        ev = run.log(ev)
        if ev["t"] == "init" and ev.get("session"):
            run.meta["session"] = ev["session"]
        self.bus.publish("run_event", {"project": p.id, "run": run.id, "event": ev})

    def _pump(self, p, run):
        last = None
        for line in run.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                self._emit(p, run, {"t": "stderr", "text": line[:2000]})
                continue
            for ev in simplify(e) or []:
                if ev["t"] == "done":
                    last = ev
                self._emit(p, run, ev)
        code = run.proc.wait()
        run.proc.stdout.close()
        m = run.meta
        turn = m["turns"][-1]
        turn["ended"] = time.time()
        turn["ok"] = bool(last and last["ok"]) and code == 0
        if last:
            m["cost"] = (m.get("cost") or 0) + (last.get("cost") or 0)
            m["denials"] = last.get("denials") or []
            m["suggested_allow"] = sorted({denial_rule(d) for d in m["denials"]} - set(m["allowed"]))
            m["questions"] = "## Questions for the founder" in (last.get("text") or "")
        if m["status"] == "cancelled":
            pass
        elif turn["ok"]:
            m["status"] = "waiting" if (m.get("questions") or m.get("suggested_allow")) else "done"
        else:
            m["status"] = "failed"
            m["exit_code"] = code
        self.live.pop(run.id, None)
        try:
            os.remove(self._lock_path(p))
        except OSError:
            pass
        run._save()
        self.bus.publish("run", {"project": p.id, "run": m})

    def _pump_err(self, p, run):
        for line in run.proc.stderr:
            if line.strip():
                self._emit(p, run, {"t": "stderr", "text": line.rstrip()[:2000]})
        run.proc.stderr.close()

    # ── reading ────────────────────────────────────────────────────────────────
    def get(self, p, rid):
        if rid in self.live:
            return self.live[rid]
        path = os.path.join(p.gdir, "runs", os.path.basename(rid) + ".json")
        try:
            with open(path, encoding="utf-8") as fh:
                meta = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        if meta.get("status") in ("running", "starting"):
            meta["status"] = "interrupted"  # the GUI stopped while it was working
        return Run(p, meta["step"], meta)

    def listing(self, p):
        d = os.path.join(p.gdir, "runs")
        out = []
        if os.path.isdir(d):
            for n in sorted(os.listdir(d), reverse=True):
                if n.endswith(".json"):
                    r = self.get(p, n[:-5])
                    if r:
                        out.append(r.meta)
        return out
