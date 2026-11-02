import json
import os
import re
import unittest

from _load import ROOT, SKILLS_DIR

SKILLS = ["founder-board", "founder-marketing", "founder-cfo", "founder-consumer", "founder-launch",
          "founder-pricing", "founder-offer", "founder-competitors", "founder-brand", "founder-ops", "founder-plan"]
ABOUT = ("Eleven free Claude skills that test a business before you launch it: a board trained on Hormozi, "
         "Thiel and Jobs, a marketing director, a CFO, and a consumer panel of 100 buyer agents. Free, MIT.")


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else ""), text


EM = chr(0x2014)  # built in code so this file does not trip its own check


def text_files():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            if f.endswith((".md", ".py", ".json", ".txt", ".ps1", ".sh")) or f in ("LICENSE", ".gitignore"):
                yield os.path.join(base, f)


class Repo(unittest.TestCase):
    def test_eleven_skill_folders(self):
        found = sorted(d for d in os.listdir(SKILLS_DIR) if os.path.isfile(os.path.join(SKILLS_DIR, d, "SKILL.md")))
        self.assertEqual(found, sorted(SKILLS))

    def test_frontmatter_name_and_description(self):
        for s in SKILLS:
            fm, text = frontmatter(os.path.join(SKILLS_DIR, s, "SKILL.md"))
            self.assertIn("name: %s\n" % s, fm + "\n", s)
            self.assertRegex(fm, r"description: ", s)
            self.assertGreater(len(fm), 300, "%s description is too thin" % s)
            self.assertGreater(len(text.splitlines()), 60, s)

    def test_tools_named_in_skills_exist(self):
        local = {
            "founder-board": ["lenses.md"],
            "founder-cfo": ["unit_economics.py"],
            "founder-consumer": ["panel.py"],
            "founder-pricing": ["van_westendorp.py"],
            "founder-plan": ["compile.py"],
        }
        for s in SKILLS:
            _, text = frontmatter(os.path.join(SKILLS_DIR, s, "SKILL.md"))
            self.assertNotRegex(text, r"\$\{CLAUDE_SKILL_DIR\}/", s)
            for name in local.get(s, []):
                self.assertIn(name, text, s)
                self.assertTrue(os.path.isfile(os.path.join(SKILLS_DIR, s, name)), "%s: %s" % (s, name))
        _, pricing = frontmatter(os.path.join(SKILLS_DIR, "founder-pricing", "SKILL.md"))
        self.assertIn("founder-cfo/unit_economics.py", pricing)
        self.assertTrue(os.path.isfile(os.path.join(SKILLS_DIR, "founder-cfo", "unit_economics.py")))

    def test_plugin_manifests(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json")) as fh:
            plugin = json.load(fh)
        self.assertEqual(plugin["name"], "founder-skill")
        self.assertEqual(plugin["description"], ABOUT)
        self.assertEqual(plugin["license"], "MIT")
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")) as fh:
            market = json.load(fh)
        self.assertEqual(market["name"], "founder-skill")
        self.assertEqual(market["plugins"][0]["name"], "founder-skill")
        self.assertEqual(market["plugins"][0]["source"], "./")
        with open(os.path.join(ROOT, ".cursor-plugin", "plugin.json")) as fh:
            cursor_plugin = json.load(fh)
        self.assertEqual(cursor_plugin["name"], "founder-skill")
        self.assertEqual(cursor_plugin["skills"], "./skills")
        self.assertTrue(os.path.isdir(os.path.join(ROOT, cursor_plugin["skills"])))
        with open(os.path.join(ROOT, ".cursor-plugin", "marketplace.json")) as fh:
            cursor_market = json.load(fh)
        self.assertEqual(cursor_market["name"], "founder-skill")
        self.assertEqual(cursor_market["plugins"][0]["name"], "founder-skill")
        self.assertEqual(cursor_market["plugins"][0]["source"], ".")

    def test_readme_carries_the_reel_copy(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = " ".join(fh.read().split())
        self.assertTrue(readme.startswith("# The Founder skill"))
        for line in (
            "Eleven Claude skills that test a business before you launch it. Free, MIT, no signup, no API key, "
            "nothing to connect.",
            "One of them is your board of directors, trained on the frameworks of Alex Hormozi, Peter Thiel and "
            "Steve Jobs. One is your marketing director. One is your CFO and finds your real profit margins. And "
            "one is the consumer panel: it spins up 100 buyer agents trained on your target customer and runs your "
            "business through 100 buyer scenarios.",
            "/founder-board",
            "~/.cursor/skills",
            ".cursor-plugin/marketplace.json",
            "scripts/install-cursor.ps1",
            "scripts/install-cursor.sh",
            "## Fine print",
        ):
            self.assertIn(line, readme)
        for s in SKILLS:
            self.assertIn("`skills/%s`" % s, readme)

    def test_cursor_skill_contract(self):
        for s in SKILLS:
            fm, text = frontmatter(os.path.join(SKILLS_DIR, s, "SKILL.md"))
            self.assertIn("disable-model-invocation: true", fm, s)
            self.assertIn("## Where this runs", text, s)
            desc = re.search(r"description: >-\n(.*?)\nargument-hint:", fm, re.S)
            self.assertIsNotNone(desc, s)
            words = " ".join(desc.group(1).split())
            self.assertLessEqual(len(words), 1024, s)
        for s in ("founder-board", "founder-consumer"):
            _, text = frontmatter(os.path.join(SKILLS_DIR, s, "SKILL.md"))
            self.assertIn("generalPurpose", text, s)
            self.assertIn("Task", text, s)
            self.assertIn("general-purpose", text, s)

    def test_install_scripts(self):
        for name in ("install-cursor.ps1", "install-cursor.sh"):
            path = os.path.join(ROOT, "scripts", name)
            with open(path, encoding="utf-8") as fh:
                script = fh.read()
            self.assertIn(".cursor", script)
            self.assertIn("skills", script)
            self.assertIn("skills-cursor", script)
            self.assertIn("founder-", script)

    def test_examples_parse(self):
        for rel in ("founder-cfo/example.json", "founder-consumer/customer.example.json"):
            with open(os.path.join(SKILLS_DIR, rel), encoding="utf-8") as fh:
                json.load(fh)

    def test_no_em_dashes(self):
        for path in text_files():
            with open(path, encoding="utf-8") as fh:
                self.assertNotIn(EM, fh.read(), os.path.relpath(path, ROOT))


if __name__ == "__main__":
    unittest.main()
