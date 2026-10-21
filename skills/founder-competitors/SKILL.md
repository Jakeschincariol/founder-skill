---
name: founder-competitors
description: >-
  Maps every competitor and the gap they leave. Finds the direct competitors,
  indirect ones and the substitutes a buyer would use instead, from public
  sources only, and records what each sells, at what price, how they position
  themselves and what their customers complain about in public reviews, every fact
  with a link. Ends with a positioning map and the gap the new business can own.
  Use when the user says "who are my competitors", "is this market crowded", "what
  else is out there", "competitor analysis", "find the gap", or "who am I up
  against".
argument-hint: "[city or market]"
---

# founder-competitors

Every buyer already solves this problem somehow. This skill finds out how, what
they pay, and what they hate about it, so the new business starts with a gap
instead of a guess.

## Founder feedback

Before anything else, read `founder/feedback/competitors.md` if it exists (the founder
writes it by hand or from Founder GUI, `gui/` in this repo). Every item under
`## Open` is a request from the founder: `change` means do it, `keep` means do not
undo it, `question` means answer it in your summary. Act on each one in this run,
then move it under `## Addressed` as `- [x] ...` with one line on what you did. If
an item cannot be done (it needs a number nobody has), leave it open and say why.

## The rules

- **Public sources only, every fact linked.** Websites, price pages, menus, app
  store and Google Maps listings, review sites, Reddit, news. If a source cannot be
  reached, say so. Never invent a competitor, a price, a rating or a review.
- **Read, do not scrape.** Read pages as a person would. Respect each site's terms.
- **Quotes are verbatim**, short, with the link. They are research, never
  testimonials.

## Step 1: who is there

From `founder/idea.md` (write it first if missing; see `/founder-board` step 0):

| type | what it means | example for a matcha café |
| --- | --- | --- |
| Direct | sells the same thing to the same buyer | other matcha bars within walking distance |
| Indirect | a different product for the same job | the coffee shops on the same street |
| Substitute | how buyers solve it without a business | matcha powder at home, canned drinks |

Aim for 5 to 10 direct and indirect, plus the main substitutes. For a local
business, search the map for the exact area; for online, search how a buyer would
("best <thing> for <who>", "<thing> alternative").

## Step 2: the facts

One row per competitor in `founder/competitors.csv`:

`name,type,url,location_or_channel,price_of_comparable_item,what_it_sells,positioning_line,rating,review_count,source_date`

`positioning_line` is their own headline or tagline, copied. Price is for the item
closest to what the new business sells, with what it includes.

## Step 3: what their customers say

For the top 3 to 5, read their reviews (1 to 3 stars first, then the "love it,
but..." 4 stars). Note recurring complaints as themes with counts and one or two
linked quotes each. Mark a theme thin if it has under three reviews.

## Step 4: the map and the gap

Write `founder/competitors.md`:

1. The table (from the CSV), sorted by how directly each competes.
2. Price range: lowest, median, highest for the comparable item.
3. A positioning map in text: two axes that matter to this buyer (price and
   convenience, quality and speed...), where each competitor sits.
4. The complaints, ranked, with links.
5. **The gap**: what nobody does well that this business could, tied to the
   evidence. If there is no gap, say so plainly; that is the most useful result
   this skill can give.
6. The threat: who could copy the new business fastest, and how.

## Output

`founder/competitors.csv`, `founder/competitors.md`. Next: `/founder-consumer`
uses the complaints to write real objections; `/founder-pricing` uses the price
range.
