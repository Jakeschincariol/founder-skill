---
name: founder-marketing
description: >-
  Your marketing director. Turns the buyer panel and the competitor map into
  positioning, the channels the target customer actually uses, a 30-day launch
  campaign with dated posts and ads, the first ten hooks, a budget split and the
  numbers to watch. Every message answers an objection real or simulated buyers
  raised. Use when the user says "how do I market this", "marketing plan", "launch
  campaign", "how do I get customers", "where do I advertise", "write my ads", or
  "positioning".
argument-hint: "[budget]"
---

# founder-marketing

A business no one hears about does not exist. This skill plans how the first
customers hear about it, using what the rest of the pack already learned instead
of a generic playbook.

## Founder feedback

Before anything else, read `founder/feedback/marketing.md` if it exists (the founder
writes it by hand or from Founder GUI, `gui/` in this repo). Every item under
`## Open` is a request from the founder: `change` means do it, `keep` means do not
undo it, `question` means answer it in your summary. Act on each one in this run,
then move it under `## Addressed` as `- [x] ...` with one line on what you did. If
an item cannot be done (it needs a number nobody has), leave it open and say why.

## Step 1: read the evidence

- `founder/panel/results.md`: who buys, who doesn't, and why. The segments with the
  highest buy rate are the first audience. The top objections are what the
  marketing must answer.
- `founder/competitors.md`: how competitors position themselves (so you do not
  sound like them) and the gap.
- `founder/offer.md` and `founder/pricing.md`: what is being sold, at what price.
- `founder/numbers.json`: what a customer is worth, which caps what you can spend to
  win one.

If none of these exist, say what is missing and offer to run `/founder-consumer
--quick` first. Do not invent an audience.

## Step 2: positioning

One line, then the reasons:

```
For <the segment that buys most>, who <their problem in their words>,
<business> is the <category> that <the gap>, unlike <the nearest alternative>.
```

Give three versions, recommend one, and say which panel evidence supports it.

## Step 3: channels

List where the first audience actually spends attention, specific to the business
type and place: foot traffic and window signage, Google Maps, Instagram and TikTok,
local creators, neighbourhood groups, partnerships with nearby businesses, email,
paid search, paid social. For each: why it fits this buyer, rough cost, and how you
will know it worked. Pick two or three to start; say what you are not doing and why.

## Step 4: the 30-day campaign

`founder/marketing.md` gets a dated calendar from launch minus 14 days to launch
plus 16: what goes out each day, on which channel, with the message. Include:

- **Ten hooks**, each answering one panel objection or using one buyer reason,
  written for the format (a 3-second opening line for video, a headline for an ad,
  a sign in the window).
- The launch-week offer from `founder/pricing.md` and when it ends.
- What to post when there is nothing new to say (behind the scenes, the making of).

## Step 5: budget and numbers

- The budget split across the chosen channels.
- The most you can pay to win a customer: from the CFO's contribution per unit and
  the panel's purchases per buyer, show the sum.
- The three numbers to watch weekly and the level that means "change something".

## Rules

- No fake reviews, follower counts, testimonials, before/afters or "as seen on".
- Panel quotes are research; never use them as customer quotes in ads.
- Disclose paid partnerships. Follow the advertising rules for claims in the user's
  market (health and earnings claims especially). Not legal advice.

## Output

`founder/marketing.md`. Next: `/founder-brand`, then `/founder-launch`.
