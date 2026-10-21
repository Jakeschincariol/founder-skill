import json
import os
import shutil
import stat
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from _load import ROOT

sys.path.insert(0, os.path.join(ROOT, "gui"))

import demo  # noqa: E402
from founder_gui import feedback, registry, rounds, runs, server, steps  # noqa: E402
from founder_gui.project import NotFound, Project  # noqa: E402

FAKE_CLAUDE = r'''#!/usr/bin/env python3
import json, os, sys
args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a") as fh:
    fh.write(json.dumps(args) + "\n")
resume = "--resume" in args
def out(e):
    print(json.dumps(e), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1", "model": "fake", "permissionMode": "acceptEdits"})
out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "python3 x.py"}}]}})
out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "fine"}]}})
text = "Done." if resume else "Wrote founder/idea.md.\n\n## Questions for the founder\n1. What is the price?"
out({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}})
denials = [] if resume else [{"tool_name": "Bash", "tool_input": {"command": "curl example.com"}}]
out({"type": "result", "subtype": "success", "is_error": False, "result": text, "total_cost_usd": 0.01,
     "num_turns": 2, "session_id": "sess-1", "permission_denials": denials})
'''


def slurp(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def build_demo(upto="plan"):
    d = tempfile.mkdtemp(prefix="fgui-")
    with open(os.devnull, "w") as null:
        old, sys.stdout = sys.stdout, null
        try:
            demo.main([d, "--upto", upto])
        finally:
            sys.stdout = old
    return d


class Steps(unittest.TestCase):
    def test_status_from_files(self):
        now = 1000.0
        files = {"idea.md": 100, "board.md": 101, "board/offers.md": 100, "competitors.csv": 102}
        st = {s["key"]: s for s in steps.status(files, now=now)}
        self.assertEqual(st["board"]["status"], "done")
        self.assertEqual(st["competitors"]["status"], "partial")
        self.assertEqual(st["consumer"]["status"], "empty")
        self.assertEqual(steps.next_step(list(st.values())), "competitors")

    def test_stale_when_a_dependency_is_newer(self):
        files = {"pitch.md": 500, "panel/results.md": 100, "customer.json": 90}
        st = {s["key"]: s for s in steps.status(files, now=10000)}
        self.assertEqual(st["consumer"]["status"], "stale")
        self.assertEqual(st["consumer"]["stale_by"], ["pitch.md"])

    def test_running_when_just_written_or_gui_run(self):
        st = {s["key"]: s for s in steps.status({"board.md": 995}, now=1000)}
        self.assertEqual(st["board"]["status"], "running")
        st = {s["key"]: s for s in steps.status({}, active_runs={"cfo"}, now=1000)}
        self.assertEqual(st["cfo"]["status"], "running")

    def test_owner(self):
        self.assertEqual(steps.owner("panel/answers/P001.json"), "consumer")
        self.assertEqual(steps.owner("cfo.md"), "cfo")
        self.assertIsNone(steps.owner("feedback/cfo.md"))


class ProjectReads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = build_demo()
        cls.p = Project(cls.dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_resolve_accepts_root_or_founder(self):
        self.assertEqual(Project(self.dir).fdir, Project(os.path.join(self.dir, "founder")).fdir)

    def test_numbers_match_the_example(self):
        a = self.p.cfo()["analysis"]
        self.assertAlmostEqual(a["contribution"], 4.76, places=2)
        self.assertEqual(round(a["year1_profit"]), 93926)
        self.assertEqual(self.p.verdict()["verdict"], "Profitable")

    def test_state_is_json_safe(self):
        st = self.p.state()
        json.dumps(st, allow_nan=False)
        self.assertEqual(len(st["steps"]), 11)
        self.assertEqual(st["name"], "Moss Matcha Bar")
        self.assertEqual(len(st["checklist"]), 5)

    def test_panel_and_pricing(self):
        pn = self.p.panel()
        self.assertEqual((pn["n"], pn["answered"]), (100, 100))
        self.assertIsNotNone(pn["live"]["buy_rate"])
        pr = self.p.pricing()
        self.assertEqual(len(pr["curves"]["grid"]), 121)
        self.assertEqual(len(pr["competitors"]), 5)

    def test_whatif_never_touches_numbers_json(self):
        path = os.path.join(self.p.fdir, "numbers.json")
        before = slurp(path)
        a = self.p.whatif({"price": 7.5, "volume": 0.8, "fixed_scale": 1.1})
        self.assertEqual(a["price"], 7.5)
        self.assertEqual(slurp(path), before)

    def test_paths_cannot_escape_founder(self):
        with self.assertRaises(NotFound):
            self.p.read("../../etc/passwd")
        with self.assertRaises(NotFound):
            self.p.brief("../x")

    def test_board_memos(self):
        b = self.p.board()
        self.assertEqual(sorted(m["lens"] for m in b["memos"]), ["monopoly", "offers", "product"])
        self.assertEqual({m["vote"] for m in b["memos"]}, {"FUND", "FUND IF", "PASS"})

    def test_checklist_tick(self):
        cid = self.p.checklist()[0]["id"]
        self.p.tick(cid, True, "panel says 38%")
        self.assertTrue(self.p.checklist()[0]["done"])


class Feedback(unittest.TestCase):
    def setUp(self):
        self.dir = build_demo("board")
        self.p = Project(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_round_trip_through_markdown(self):
        feedback.add(self.p, "board", "change", "Score on weekdays", "board/offers.md")
        feedback.add(self.p, "board", "question", "Why three members?")
        f = feedback.read(self.p, "board")
        self.assertEqual([i["kind"] for i in f["open"]], ["change", "question"])
        self.assertEqual(f["open"][0]["ref"], "board/offers.md")
        f = feedback.resolve(self.p, "board", 0)
        self.assertEqual(len(f["open"]), 1)
        self.assertEqual(f["addressed"][0]["text"], "Score on weekdays")
        text = slurp(os.path.join(self.p.fdir, "feedback", "board.md"))
        self.assertIn("## Open", text)
        self.assertIn("- [x] change: Score on weekdays (on board/offers.md)", text)

    def test_reads_what_a_skill_wrote_by_hand(self):
        os.makedirs(os.path.join(self.p.fdir, "feedback"))
        with open(os.path.join(self.p.fdir, "feedback", "cfo.md"), "w") as fh:
            fh.write("# Feedback\n\n## Open\n- [ ] keep: the ramp\n\n## Addressed\n- [x] change: rent is 11k (done: updated)\n")
        f = feedback.read(self.p, "cfo")
        self.assertEqual(f["open"][0]["kind"], "keep")
        self.assertEqual(len(f["addressed"]), 1)

    def test_rejects_unknown_step_and_empty_text(self):
        with self.assertRaises(ValueError):
            feedback.add(self.p, "nope", "change", "x")
        with self.assertRaises(ValueError):
            feedback.add(self.p, "board", "change", "  ")

    def test_every_skill_reads_its_feedback_file(self):
        for key, skill, _, _, _ in steps.STEPS:
            with open(os.path.join(ROOT, "skills", skill, "SKILL.md"), encoding="utf-8") as fh:
                self.assertIn("founder/feedback/%s.md" % key, fh.read(), skill)


class Rounds(unittest.TestCase):
    def test_snapshot_and_compare(self):
        d = build_demo()
        try:
            p = Project(d)
            r1 = rounds.snapshot(p, "Pitch v1")
            self.assertTrue(r1["id"].endswith("pitch-v1"))
            with open(os.path.join(p.fdir, "offer.md"), "a") as fh:
                fh.write("\nA new bonus.\n")
            c = rounds.compare(p, r1["id"], "current")
            self.assertIn("offer.md", c["changed"])
            self.assertEqual(c["a"]["metrics"]["verdict"], "Profitable")
            self.assertEqual(rounds.as_project(p, r1["id"]).name(), "Moss Matcha Bar")
            self.assertEqual(len(rounds.listing(p)), 1)
            with self.assertRaises(ValueError):
                rounds.as_project(p, "../../x")
        finally:
            shutil.rmtree(d, ignore_errors=True)


class Runs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fgui-run-")
        self.fake = os.path.join(self.tmp, "claude")
        with open(self.fake, "w") as fh:
            fh.write(FAKE_CLAUDE.replace("#!/usr/bin/env python3", "#!" + sys.executable))
        os.chmod(self.fake, os.stat(self.fake).st_mode | stat.S_IEXEC)
        self.log = os.path.join(self.tmp, "args.log")
        os.environ.update(FOUNDER_GUI_CLAUDE=self.fake, FAKE_LOG=self.log)
        self.p = Project(os.path.join(self.tmp, "proj"))
        self.m = runs.Manager(server.Bus())

    def tearDown(self):
        os.environ.pop("FOUNDER_GUI_CLAUDE", None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wait(self, rid):
        for _ in range(100):
            if rid not in self.m.live:
                return self.m.get(self.p, rid).meta
            time.sleep(0.05)
        self.fail("run did not finish")

    def test_run_asks_then_resumes_with_allowed_tool(self):
        meta = self.m.start(self.p, "board", "--quick", force=True)
        with self.assertRaises(runs.Busy):
            self.m.start(self.p, "cfo", force=True)  # one GUI run per project
        meta = self.wait(meta["id"])
        self.assertEqual(meta["status"], "waiting")
        self.assertEqual(meta["session"], "sess-1")
        self.assertTrue(meta["questions"])
        self.assertEqual(meta["suggested_allow"], ["Bash(curl:*)"])
        first = json.loads(slurp(self.log).splitlines()[0])
        self.assertEqual(first[1], "/founder-skill:founder-board --quick")
        self.assertIn("--plugin-dir", first)
        self.assertIn("none", first)  # --permission-prompts none: headless never hangs on a prompt

        self.m.reply(self.p, meta["id"], "The price is $6.50", allow=["Bash(curl:*)"])
        meta = self.wait(meta["id"])
        self.assertEqual(meta["status"], "done")
        second = json.loads(slurp(self.log).splitlines()[1])
        self.assertEqual(second[second.index("--resume") + 1], "sess-1")
        self.assertIn("Bash(curl:*)", second)
        kinds = [e["t"] for e in self.m.get(self.p, meta["id"]).events()]
        self.assertEqual(kinds.count("prompt"), 2)
        self.assertIn("tool", kinds)
        self.assertIsNone(self.m.active(self.p))

    def test_simplify_skips_noise(self):
        self.assertIsNone(runs.simplify({"type": "system", "subtype": "hook_started"}))
        self.assertEqual(runs.denial_rule({"tool": "Bash", "input": {"command": "git status"}}), "Bash(git:*)")
        self.assertEqual(runs.denial_rule({"tool": "WebFetch", "input": {}}), "WebFetch")


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = tempfile.mkdtemp(prefix="fgui-home-")
        os.environ["FOUNDER_GUI_HOME"] = cls.home
        cls.dir = build_demo()
        cls.pid = registry.add(cls.dir).id
        cls.app, cls.httpd = server.serve(0)
        cls.port = cls.httpd.server_address[1]
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.app.watcher.stop()
        os.environ.pop("FOUNDER_GUI_HOME", None)
        shutil.rmtree(cls.home, ignore_errors=True)
        shutil.rmtree(cls.dir, ignore_errors=True)

    def call(self, path, method="GET", body=None, headers=None):
        h = {"Content-Type": "application/json"}
        h.update(headers or {})
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.port, path), method=method, headers=h,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read()

    def test_ping_and_views(self):
        code, body = self.call("/api/ping")
        self.assertEqual((code, json.loads(body)["app"]), (200, "founder-gui"))
        for view in ("state", "board", "competitors", "panel", "pricing", "cfo", "offer", "feedback", "runs"):
            code, body = self.call("/api/p/%s/%s" % (self.pid, view))
            self.assertEqual(code, 200, view)
        code, body = self.call("/")
        self.assertIn(b"Founder GUI", body)

    def test_writes_need_the_header(self):
        code, _ = self.call("/api/p/%s/rounds" % self.pid, "POST", {"label": "x"})
        self.assertEqual(code, 403)
        code, _ = self.call("/api/p/%s/feedback/board" % self.pid, "POST", {"text": "hi"}, {server.HEADER: "1"})
        self.assertEqual(code, 200)

    def test_foreign_host_is_refused(self):
        code, _ = self.call("/api/ping", headers={"Host": "evil.example:80"})
        self.assertEqual(code, 403)

    def test_static_cannot_escape(self):
        code, _ = self.call("/static/../founder_gui/server.py")
        self.assertEqual(code, 404)

    def test_export_is_self_contained(self):
        code, body = self.call("/api/p/%s/export" % self.pid)
        html = body.decode()
        self.assertEqual(code, 200)
        self.assertIn("window.__FOUNDER_SNAPSHOT__", html)
        self.assertNotIn('src="/static/', html)
        self.assertNotIn('href="/static/', html)


if __name__ == "__main__":
    unittest.main()
