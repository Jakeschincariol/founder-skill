---
name: founder-board
description: >-
  Your board of directors. Puts a business idea in front of a three-member board,
  each a sub-agent reading the idea through one published framework: the Offers
  lens (from Alex Hormozi's $100M Offers), the Monopoly lens (from Peter Thiel's
  Zero to One) and the Product lens (from Walter Isaacson's biography of Steve
  Jobs). Each member scores the idea, names the risks that would kill it and votes
  fund, fund with conditions, or pass. Use when the user says "test my business
  idea", "would this work", "pressure-test this", "what would a board say", "is
  this a good business", or starts the founder pack on a new idea.
argument-hint: "<the business idea, or leave blank to use the conversation>"
---

# founder-board

The first meeting. Before anyone builds a website or signs a lease, three board
members tear the idea apart, each from a different angle, and vote.

What the user typed after `/founder-board`: `$ARGUMENTS`. If that is blank, take
the idea from the conversation.

## Founder feedback

Before anything else, read `founder/feedback/board.md` if it exists (the founder
writes it by hand or from Founder GUI, `gui/` in this repo). Every item under
`## Open` is a request from the founder: `change` means do it, `keep` means do not
undo it, `question` means answer it in your summary. Act on each one in this run,
then move it under `## Addressed` as `- [x] ...` with one line on what you did. If
an item cannot be done (it needs a number nobody has), leave it open and say why.

## The rule about the three names

The lenses are summaries of **published frameworks**, nothing more. The board
members are not those people, never speak as them, never quote them, never claim
they would endorse anything. Write "the Offers lens", never "Alex Hormozi says".
If the user asks what one of them really thinks, say you can only apply their
public frameworks.

## Step 0: the idea file

Everything in the founder pack reads `founder/idea.md` in the user's project. If
it does not exist, write it now from the conversation:

```markdown
# <business name, or a working name>

- What it is: one sentence.
- Who it is for: the target customer, as specific as the user can make it.
- What it sells, at what price: the core product and its price.
- Where and how: city or online, how customers find it, how it is delivered.
- Budget and constraints: money, time, skills, anything already decided.
```

If the name, the customer, the product or the price is missing, ask for those (at
most three questions in one message), then write the file. Do not invent a
budget, a market size or a competitor.

## Step 1: brief the board

Write `founder/board/brief.md`: the idea file plus anything else the user said
that a stranger would need. **Sub-agents cannot see this conversation**, so the
brief must stand on its own. Do not add your own opinion of the idea to it.

## Step 2: convene

Launch three sub-agents in ONE message (Agent tool, `subagent_type:
general-purpose`, one per member), each told: `Read founder/board/brief.md and
founder-board's lenses.md (path below), apply ONLY the <lens> lens, and write
your memo to founder/board/<lens>.md.` The lens file is `lenses.md` in this
skill's folder (`${CLAUDE_SKILL_DIR}/lenses.md`; if that path is not expanded,
use the base directory Claude Code printed for this skill).

Each memo, in this shape:

```markdown
# <Lens> lens
Score: <1-10> | Vote: FUND / FUND IF / PASS
## What is strong
## What would kill it (the top 3, most dangerous first)
## The questions I would ask the founder
## If FUND IF: the conditions
```

## Step 3: the chair's summary

Read the three memos (they are short) and write `founder/board.md`:

1. The vote, e.g. "2 fund if, 1 pass", and the average score.
2. The risks more than one member raised: these go first.
3. Every condition, merged, as a checklist the rest of the pack can tick off
   (the CFO, the consumer panel and pricing will test most of them).
4. One paragraph: the strongest version of this business the board can see.
   It may differ from what the user pitched; say so plainly.

Keep the members' disagreements. A board that agrees on everything was not doing
its job.

## Rules

- Score the business, not the founder.
- No made-up facts. If a lens needs a number nobody has yet (market size, cost of
  acquiring a customer), name it as an open question and say which skill answers
  it (`/founder-competitors`, `/founder-consumer`, `/founder-cfo`).
- A PASS is a result, not a failure. Say it plainly.

## Output

`founder/idea.md`, `founder/board/` (brief and three memos), `founder/board.md`.
Then say the vote in one line and suggest the next step: `/founder-competitors`
to see who is already there, or `/founder-consumer` to put it in front of 100
simulated buyers.

## Where the pack goes next

```
board -> competitors -> consumer -> pricing -> offer -> cfo -> marketing -> brand -> ops -> launch -> plan
```

Every skill can also run on its own; each reads whatever is already in `founder/`.
