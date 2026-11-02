---
name: founder-plan
description: >-
  Your business planner. Compiles everything the other founder skills wrote (the
  board's verdict, the competitors, the buyer panel, pricing, the offer, the CFO's
  numbers, marketing, brand, operations and the launch plan) into one business
  plan with a verdict at the top that is computed from the numbers, never written
  by hand: Profitable, Not yet (with the failing numbers) or Incomplete. Adds an
  executive summary and a one-page version for a partner, lender or investor. Use
  when the user says "write my business plan", "put it all together", "is it
  profitable", "give me the plan", or at the end of the founder pack.
argument-hint: "[--min-buy-rate 0.25]"
disable-model-invocation: true
---

# founder-plan

## Where this runs

The text after this skill's slash command in the message that invoked it is the argument. If `$ARGUMENTS` was replaced with that text, use the replacement. If the message is only the command, the argument is blank and the rules already in this skill apply.

This skill's folder is the directory of this `SKILL.md`. Run Python with `python` on Windows, and with `python3` when that is the command on PATH. If `${CLAUDE_SKILL_DIR}` is expanded, it is the same folder.

Write `founder/` at the root of the open project. Never write it inside the installed skill folder.

The last step. One document a founder can act on, or hand to a partner or a
lender, built only from what the pack found.

Tool in this folder:

```bash
python "<this skill's folder>/compile.py" --dir founder
```

## Step 1: see what is there

```bash
python "<this skill's folder>/compile.py" --dir founder --check
```

prints the verdict and each check. The checks, all computed:

1. Each unit earns money before fixed costs (`founder/numbers.json`).
2. Year 1 makes an operating profit.
3. The break-even fits inside capacity, if a capacity was given.
4. Enough simulated buyers buy (`founder/panel/results.json`; default bar 25%,
   change it with `--min-buy-rate` and say why).

If there are no numbers, the verdict is Incomplete: offer to run `/founder-cfo`.
List the other missing sections with the skill that fills each. Do not fill a
missing section yourself from guesses.

## Step 2: the summary

Write `founder/summary.md`, half a page, plain words:

- What the business is and who it is for, in two sentences.
- The verdict and the three numbers behind it (margin, break-even, year 1).
- What the buyer panel and the board agreed on, and where they disagreed.
- The biggest risk and what will be done about it.
- What the founder needs to start (cash from the CFO, the first test from launch).
- The one thing to do this week.

If the verdict is Not yet, the summary leads with what has to change and which skill
changes it. Never soften a failing check.

## Step 3: compile

```bash
python "<this skill's folder>/compile.py" --dir founder
```

writes `founder/business-plan.md`: title, the verdict and its checks, the key numbers
table, the idea, then every section the pack produced (summary, board, competition,
panel, pricing, offer, numbers, marketing, brand, operations, launch), and what is
not done yet.

## Step 4: the one-pager

Write `founder/one-pager.md` for someone deciding in two minutes: the problem, the
customer, the offer and price, the numbers table, the evidence (panel result,
competitor gap, any real test), what the money is for, and the ask. Same numbers as
the plan, word for word.

## Rules

- The verdict comes from `compile.py`. Never write Profitable by hand, and never
  round a failing number into a passing one.
- Say once, clearly: the panel is simulated buyers and the numbers are projections;
  real customers and real quotes confirm them. Not financial, legal or tax advice.
- If the user wants a PDF or a deck, offer to export the plan, but keep the
  markdown as the source of truth.

## Output

`founder/summary.md`, `founder/business-plan.md`, `founder/one-pager.md`. Then give
the user the verdict in one line and the one thing to do this week.
