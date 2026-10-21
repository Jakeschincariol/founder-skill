---
name: founder-cfo
description: >-
  Your CFO. Builds the unit economics of a business before money is spent: what
  one unit earns after its direct costs, the real profit margin at the planned
  volume, the break-even point in units a day, year 1 month by month, the cash
  needed before it pays for itself, how long the startup spend takes to earn back,
  and what happens if the price drops, sales come in low or costs rise. Every
  number traces to an input the user can check. Use when the user says "find the
  profit margins", "do the numbers", "is this profitable", "break-even", "unit
  economics", "how much do I need to start", or "run the CFO".
argument-hint: "[path to numbers.json]"
---

# founder-cfo

The person who asks "and what does that cost?" Margins decide whether a good idea
is a business. This skill finds them, with every number traceable to an input.

Tool in this folder:

```bash
python3 "${CLAUDE_SKILL_DIR}/unit_economics.py" founder/numbers.json --out founder/cfo.md
```

## Founder feedback

Before anything else, read `founder/feedback/cfo.md` if it exists (the founder
writes it by hand or from Founder GUI, `gui/` in this repo). Every item under
`## Open` is a request from the founder: `change` means do it, `keep` means do not
undo it, `question` means answer it in your summary. Act on each one in this run,
then move it under `## Addressed` as `- [x] ...` with one line on what you did. If
an item cannot be done (it needs a number nobody has), leave it open and say why.

## Step 1: gather the inputs

Write `founder/numbers.json` (shape: `example.json` in this folder, a walk-in
matcha café). It needs:

| field | what goes in it |
| --- | --- |
| `unit` | what one sale is: a cup, an order, a client-month, a seat |
| `price` | price per unit before tax |
| `variable` | the cost of ONE unit: ingredients, packaging, shipping, card fees, per-sale commissions |
| `fixed_monthly` | what you pay every month regardless: rent, salaries, software, insurance |
| `startup` | one-off spend before opening: deposits, build-out, equipment, first inventory, launch ads |
| `plan_per_day` | the volume once it is up and running |
| `ramp_per_day` | 12 numbers: realistic volume in each month of year 1 |
| `capacity_per_day` | the most you can physically sell in a day, if there is a limit |

Where the numbers come from, in this order:

1. The user's own quotes, invoices, leases and supplier price lists.
2. Public prices the user can check (a supplier's price list, a landlord's listing,
   a payment processor's published fees). Write the source next to the number in
   `founder/cfo-sources.md`.
3. Your estimate, clearly marked as an estimate, with the reasoning. Never present
   an estimate as a fact.

Ask the user for anything only they know (rent quoted, wages they will pay). Use the
price from `founder/pricing.md` or `founder/pitch.md` if those exist.

**The ramp is where plans lie.** Month 1 is almost never the plan volume. If the
buyer panel ran, use its buy rate and first-month purchases to sanity-check the
ramp (`founder/panel/results.md`), and say how you did it.

## Step 2: run it

```bash
python3 "${CLAUDE_SKILL_DIR}/unit_economics.py" founder/numbers.json --out founder/cfo.md
```

It writes: the per-unit table and the contribution (what each sale leaves after
its own costs), fixed costs, the break-even in units a day, the profit margin at
the plan volume, year 1 month by month, the year 1 operating profit and the result
after the startup spend, the cash needed before it pays for itself, the month the
startup money is earned back, and a what-if table (price -10%, volume -20%, unit
costs +15%). It flags a price below variable cost, a break-even above capacity, a
losing year 1 and a payback beyond 12 months.

What-ifs without editing the file:

```bash
python3 "${CLAUDE_SKILL_DIR}/unit_economics.py" founder/numbers.json --price 7.00
python3 "${CLAUDE_SKILL_DIR}/unit_economics.py" founder/numbers.json --volume 0.8
```

## Step 3: the CFO's note

Add a short section at the top of `founder/cfo.md`, in plain words:

- **The margin**: the profit margin at plan, and the contribution per unit.
- **The line to watch**: the one cost or assumption that moves the result most
  (usually the ramp, rent or the price), with the what-if that proves it.
- **Cash**: how much money the founder needs before it pays for itself.
- **Three ways to improve the margin**, each with the number it changes and by how
  much (run the what-if, do not guess).
- Whether the board's conditions about money (`founder/board.md`) are met.

## Rules

- Every number in your note comes from the tool's output or an input you can name.
- Revenue is before tax; say if the user's market adds sales tax on top.
- Not financial, tax or legal advice. Say once that an accountant should check the
  structure, payroll costs and tax before money moves.

## Output

`founder/numbers.json`, `founder/cfo.md`, `founder/cfo-sources.md`. Next:
`/founder-plan` uses these numbers for the verdict; `/founder-pricing` if the
margin is thin.
