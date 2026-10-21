# Founder GUI

A local web page that follows the founder skills while they run: every step,
every suggestion, every result, live. It reads the same `founder/` folder the
skills write, and every number comes from the skills' own Python tools, so the
page and the terminal never disagree.

Standard library only, like the rest of the pack. Python 3.8 or newer, nothing
to install, no network: the server listens on 127.0.0.1.

```bash
python3 gui/serve.py --dir path/to/project     # opens the browser
python3 gui/demo.py /tmp/moss-demo              # a demo project from the matcha café example
python3 gui/serve.py --dir /tmp/moss-demo
```

From Claude Code, with the plugin installed: `/founder-skill:founder-gui`.

![The pipeline view](../docs/screenshots/pipeline.png)

## What it shows

| view | what is on it |
| --- | --- |
| Pipeline | the eleven steps with their status (not started, partial, done, re-run, running), the computed verdict and its checks, the board's conditions as a checklist, the next step |
| Board | the three memos side by side: score, vote, risks, conditions |
| Competitors | the table from `competitors.csv` and price against rating |
| Panel | the 100 buyers as tiles that fill in as answers arrive; filter by segment, behaviour, answer; open a buyer for the persona, the answer and the brief it got; buy rate by segment, behaviour and income; why they pass, why they buy, what would flip a no |
| Pricing | the Van Westendorp curves with the acceptable range, your price, competitor prices and the unit cost |
| Offer | the pitch before and after, word by word |
| CFO | the key numbers, year 1 month by month, the three what-ifs, and a what-if simulator (price, volume, unit, fixed and startup costs) that runs `unit_economics.py` on a copy |
| Docs | every file in `founder/`, rendered |
| Feedback | what you asked each skill to change, keep or answer |
| Rounds | dated copies of `founder/`, compared side by side |
| Runs | run a step from the browser and keep talking to it |

![The consumer panel, with one buyer open](../docs/screenshots/panel.png)

## The four phases

1. **Live viewer.** The hub polls `founder/` once a second and pushes changes to
   the page (server-sent events). A step counts as running while its files keep
   changing, and as "re-run" when a file it depends on changed after it ran
   (for example `pitch.md` rewritten by the offer after the panel saw it).
2. **Analysis.** The what-if simulator, the price curves, rounds and their
   comparison, and **Export HTML**: one self-contained file, the same page with
   the data frozen inside, that opens anywhere, offline, read-only.
3. **Feedback back to Claude.** Press 💬 on any paragraph (or use the Feedback
   view) to leave a `change`, `keep` or `question`. It goes to
   `founder/feedback/<step>.md`, a plain markdown file. Every skill
   reads its file before it starts, acts on the open items and moves them to
   Addressed.
4. **Runs from the web.** Starts `claude -p "/founder-skill:founder-<step>"` in
   the project folder, with this repo's skills (`--plugin-dir`), and streams it
   to the page. A headless session cannot ask questions or wait for a permission
   prompt, so the skill lists its questions at the end and you answer in the
   page (the answer resumes the same session), and blocked tool calls come back
   as "allow and continue".

## Several projects, several sessions

**One hub for every project.** The first `/founder-gui` starts the hub
(`~/.founder-gui/hub.json` says where it is); later ones, from other folders or
other Claude sessions, only add their folder to it. The sidebar lists them all.

**Two sessions in the same folder** is the case to avoid: the skills do not lock
files, so two sessions running the same step overwrite each other. The GUI
cannot stop a terminal session, but it:

- shows a warning when more than one Claude session has the folder open (via `lsof`);
- allows one GUI run per project at a time (`founder/.gui/run.lock`), and asks you
  to confirm before starting one next to an open terminal session;
- offers rounds for the real need behind it, testing two versions: run one, save
  a round, change it, run again, compare.

## Files

The GUI only writes in two places inside `founder/`:

- `founder/.gui/`: its own state (rounds, run logs, checklist ticks, the run lock);
- `founder/feedback/`: the feedback files, which the skills read on purpose.

## Security

The hub can start Claude sessions, so: it binds to 127.0.0.1, refuses any Host
header other than localhost (DNS rebinding), and every write needs an
`X-Founder-GUI` header that a page on another site cannot send without a CORS
preflight, which the hub never answers.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

`tests/test_gui.py` builds the demo project, checks every view against the
example numbers, round-trips the feedback files, compares rounds, and runs the
phase 4 flow against a fake `claude` (no tokens spent).
