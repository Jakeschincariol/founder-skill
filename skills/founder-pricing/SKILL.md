---
name: founder-pricing
description: >-
  Finds the price buyers will actually pay. Reads the consumer panel's four price
  answers per buyer into a Van Westendorp price-sensitivity range (too cheap, a
  bargain, getting expensive, too expensive), sets it against what competitors
  really charge and against the CFO's margin, and recommends a price, a price
  ladder (good / better / best) and an opening offer to test. Use when the user
  says "how much should I charge", "price this", "is $X too expensive", "pricing
  strategy", "what price", or after the consumer panel.
argument-hint: "[current price]"
---

# founder-pricing

Price is the fastest lever on the margin and the one founders guess most. This
skill sets it from three things you can check: what buyers said, what competitors
charge, and what the business needs to earn.

Tool in this folder:

```bash
python3 "${CLAUDE_SKILL_DIR}/van_westendorp.py" founder/panel/answers --price 6.50 --out founder/pricing-curve.md
```

## Founder feedback

Before anything else, read `founder/feedback/pricing.md` if it exists (the founder
writes it by hand or from Founder GUI, `gui/` in this repo). Every item under
`## Open` is a request from the founder: `change` means do it, `keep` means do not
undo it, `question` means answer it in your summary. Act on each one in this run,
then move it under `## Addressed` as `- [x] ...` with one line on what you did. If
an item cannot be done (it needs a number nobody has), leave it open and say why.

## Step 1: what buyers said

If `/founder-consumer` ran, every buyer answered four price questions. Run the
tool on `founder/panel/answers` (or a CSV with the columns `too_cheap, cheap,
expensive, too_expensive` from real surveys, which beat simulated answers every
time). It reports:

| point | meaning |
| --- | --- |
| PMC | below this, too many think it is too cheap to be good |
| OPP | the price with the least resistance either way |
| IPP | where as many call it a bargain as call it expensive |
| PME | above this, too many will not buy at all |

PMC to PME is the acceptable range. If the panel has not run, say so and offer to
run `/founder-consumer --quick` first. Do not invent a range.

## Step 2: what competitors charge

From `founder/competitors.md` (or look them up now, from their own public price
pages, with links): the price of the nearest substitutes for the same job. Note
what each price includes, so you compare like with like. A matcha latte is
compared with other matcha lattes and with the coffee it replaces, not with a tea
bag.

## Step 3: what the business needs

From `founder/numbers.json`: the variable cost per unit and the break-even. Run the
CFO's tool at two or three candidate prices to see the margin and break-even at
each:

```bash
python3 "${CLAUDE_SKILL_DIR}/../founder-cfo/unit_economics.py" founder/numbers.json --price 7.00
```

## Step 4: decide

Write `founder/pricing.md`:

1. **The price**, and why: where it sits in the acceptable range, against the
   competitors, and the margin it gives (from the tool, not a guess).
2. **The ladder**, if the business can have one: a good / better / best (size,
   bundle, subscription, membership) with a reason to step up each rung.
3. **The opening offer**: an intro price or bonus for launch that does not train
   buyers to wait for discounts, with an end date.
4. **What to test with real buyers**: two prices inside the range and how to test
   them (two landing pages, a pre-sale at each, A/B on the menu board).
5. The panel's verbatim price objections (top three), so marketing can answer them.

## Rules

- Price answers from simulated buyers pick what to test. They are not proof.
- Never price below variable cost to "buy" customers without saying so, and how
  long the CFO says the business can afford it.
- No fake anchors: no "was $X" price that was never charged.

## Output

`founder/pricing-curve.md`, `founder/pricing.md`. If the price changed, update
`founder/numbers.json` and re-run `/founder-cfo`. Next: `/founder-offer`.
