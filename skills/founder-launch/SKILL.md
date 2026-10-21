---
name: founder-launch
description: >-
  Your launch lead. Builds a dated, step-by-step launch plan: a cheap real-world
  test first (a waitlist, a pre-sale or a pop-up with a real price, so real buyers
  confirm what the simulated panel said), then the countdown to opening day with
  owners and deadlines, the launch-day run sheet, and the first 30 days of what to
  measure and what to change. Use when the user says "how do I launch", "launch
  plan", "when can I open", "launch checklist", "go live", or "soft open".
argument-hint: "[target launch date]"
---

# founder-launch

Launching is a project with a date. This skill turns everything else in the pack
into a dated plan, and starts with the cheapest way to find out if real people
will pay before the big money goes out.

## Founder feedback

Before anything else, read `founder/feedback/launch.md` if it exists (the founder
writes it by hand or from Founder GUI, `gui/` in this repo). Every item under
`## Open` is a request from the founder: `change` means do it, `keep` means do not
undo it, `question` means answer it in your summary. Act on each one in this run,
then move it under `## Addressed` as `- [x] ...` with one line on what you did. If
an item cannot be done (it needs a number nobody has), leave it open and say why.

## Step 1: test before you spend

Pick the cheapest real test that fits the business, and run it before signing the
big costs in `founder/numbers.json`:

| business | the test |
| --- | --- |
| physical shop or café | a pop-up, a market stall or a pre-order list with a price and a date |
| online product | a landing page with the price and a "pre-order" or "join the waitlist" button |
| service or agency | three paid pilot clients at the planned price |
| subscription | a founding-member offer, paid up front |

Write the success line before running it (for example: 50 pre-orders in two weeks
at $6.50), and compare the result with the panel's buy rate. If real buyers fall
well short of the panel, trust the real buyers and go back to `/founder-offer` or
`/founder-pricing`.

## Step 2: the countdown

From today to launch day, with real dates (ask for the target date; default to the
earliest realistic one given lead times in `founder/ops.md`). Weekly blocks, each
task with an owner and a deadline:

- Legal and money: registration, bank account, permits from `founder/ops.md`.
- Build: fit-out or website, suppliers ordered by their lead times.
- Brand: sign, packaging, profiles from `founder/brand.md`.
- Marketing: the calendar in `founder/marketing.md` from launch minus 14 days.
- Team: hiring and training on the SOPs.
- A soft open or friends-and-family day before the public launch.

Mark the critical path: the tasks that move the launch date if they slip.

## Step 3: launch day

An hour-by-hour run sheet: who is where, what goes out on which channel, the
opening offer, what to do if something breaks (from the risk register).

## Step 4: the first 30 days

The weekly numbers to track (from the CFO: units a day against break-even; from
marketing: the channel numbers), the level that triggers a change, and a review on
days 7, 14 and 30 with the questions to answer.

## Output

`founder/launch.md` with the test, the countdown, the run sheet and the 30-day
review. Next: `/founder-plan` compiles everything into the business plan.
