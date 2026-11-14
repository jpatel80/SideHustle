# Autopilot: how this runs with minutes of owner time (v1, 2026-11-14)

The aim is a business the owner touches for minutes a week. Some steps cannot be automated or made passive; they are listed plainly at the end.

## The loop

```
research gate -> brief (book.json + 50 page ideas) -> book factory -> upload kit -> OWNER uploads -> tracker -> decision
      ^                                                                                                      |
      +------------------------------ next book only where the data says so <-------------------------------+
```

| Step | Tool | Who | Human checkpoint |
|---|---|---|---|
| 1. Find niches | `scripts/research_niches.py harvest` then `rank` | Claude | none (free, no login) |
| 2. Check competition | `research/competitors/<keyword>.csv` (10 rows) | owner's browser, or the owner by hand, about 10 minutes per keyword | **yes**: Amazon pages are not scraped |
| 3. Brief | `books/NNN-slug/book.json` + `subjects.txt` | Claude | owner says "go" for a batch (project rule) |
| 4. Pages | `book_factory.py pages --generate` | Claude | capped spend; Claude looks at every contact sheet |
| 5. Build | `book_factory.py finish --reviewed` | Claude | refuses without the review flag or with open QA flags |
| 6. Upload | `books/NNN-slug/listing.md` (the upload kit) | **owner**, about 10 minutes | owner publishes; proof copy for a new style |
| 7. Track | `sales_tracker.py` on the monthly KDP report | owner downloads (2 minutes), Claude runs | none |
| 8. Decide | `tracking/REPORT.md` | Claude proposes, owner agrees | kill rule below |

## Research gate (steps 1-2)

- **Demand proxy, automatic:** Amazon's public search-suggestion endpoint, asked slowly with a plain client for each seed in `research/seeds.txt` plus "seed a" to "seed z". A phrase suggested early for a short prefix is typed often. It is a ranking, not a search volume, and says nothing about competition. Banned and off-brand phrases (`prompts/banned_terms.txt`: brands, characters, educational and health wording) are dropped.
- **Competition, manual or browser-sourced:** one worksheet per keyword with the first 10 organic results. Columns, in this order:
  `keyword, position, title, author, asin, bsr, reviews, rating, price, pages, pub_date, series, notes`
  Create an empty one with `python3 scripts/research_niches.py worksheet "<keyword>"`.
- **Verdict:** **GO** when at least 3 of the top 10 sell (Best Sellers Rank 150,000 or better) although they have 150 or fewer reviews or were published in the last 18 months. **MAYBE** for 1-2. **NO** when fewer than 3 sell at all, or every seller is entrenched. **UNVERIFIED** without a worksheet: no book is built. The thresholds are my starting values **[verify]**; adjust them once real sales exist.
- First harvest (2026-11-14, 810 prefixes): `research/niches_2026-11-14.md`. Everything in it is UNVERIFIED until worksheets are filled. Worth checking first: "bold and easy coloring book for adults", "cozy coloring book for adults", "winter coloring book for kids ages 4-8", "dinosaur coloring book for toddlers", "coloring book for toddlers 1-3", "easter coloring book bold and easy" (seasonal: must be live by late January).

## Book factory (steps 3-5)

One config file per book, three commands, same result every time:

```bash
python3 scripts/book_factory.py check  books/NNN-slug            # free: rules, banned terms, repeats, pricing
python3 scripts/book_factory.py pages  books/NNN-slug --generate # paid, capped by budget_usd and the $25 total
python3 scripts/book_factory.py finish books/NNN-slug --reviewed # interior, cover, upload kit, archive
```

`check` blocks: brand or character names, educational or health wording, "Little Fox" without "Paper Co", the brand in the Author field, a cover badge or subtitle that disagrees with the picture count, a missing black-and-white note, a price below KDP's minimum. It warns about page ideas repeated from another book, thin books and low royalties.

Defaults for new books: 50 pictures, 106 pages, $9.99, one niche keyword with a GO verdict.

## Upload kit (step 6)

`books/NNN-slug/listing.md` is generated, never hand-written: files, every form field in KDP's order, description, 7 keywords, 3 categories, the AI-disclosure answers, price with the royalty table, and a pre-publish checklist. A copy sits in `final/UPLOAD_KIT.md`.

## Tracking and the kill rule (steps 7-8)

Owner, once a month: download the KDP royalties report (.xlsx or .csv) into `tracking/kdp_reports/` (or upload it in a session). `python3 scripts/sales_tracker.py` then writes `tracking/REPORT.md`:

| Situation | Decision |
|---|---|
| live under 60 days | TOO EARLY |
| live 60+ days, no sale in the last 60 | RETIRE NICHE: leave the listing up, build nothing more like it |
| 8 or more copies in the last 30 days | SCALE: a sibling title or volume 2 in the same niche |
| anything else | HOLD: one listing fix, look again in 30 days |
| 90 days after the first book, nothing at SCALE | STOP adding money |

The report layout of KDP's download is matched by column names; the exact menu path and file layout are **[verify]** with the first real report.

## Owner routine

- **Per book (about 15 minutes):** look at the cover and contact sheets Claude sends, say yes or no; upload with the kit; tell Claude the publication date.
- **Per new style (once):** order a proof copy and look at it.
- **Monthly (about 5 minutes):** download the KDP report, give it to Claude, read the one-page report.
- **Per niche candidate (about 10 minutes, only until a browser is linked):** fill one competitor worksheet.
- **Once:** KDP account, tax interview, pen-name search (`research/pen_names.md`).

## Ads test (designed, DISABLED: owner decision 2026-11-14)

If the owner enables it later: one Sponsored Products automatic campaign on the single best book, $3 a day, 14 days, default bids, about $42. Read: impressions, clicks, orders. Fewer than 1 click per 300 impressions points to the cover or title; clicks without orders point to price, Look Inside or reviews. Stop at day 14 whatever happens. It needs the owner's Amazon Ads account; Claude cannot run it.

## What cannot be automated or made passive

- **Upload and Publish** on KDP: owner only (no API; Claude never logs in).
- **Tax interview, bank details, identity check:** owner only.
- **Looking at Amazon's result pages** for the competitor worksheets, until the owner links a browser.
- **Proof copies:** ordering and judging the printed book.
- **Reviews:** cannot be bought, swapped or requested from friends and family (Amazon's rules). They arrive slowly or not at all.
- **Ads:** owner's account and money; disabled.
- **Judgment on art:** the QA script catches mechanical faults only; a person or Claude must look at every page.
- **Demand:** nothing here creates buyers. A good book in a niche nobody searches earns nothing.

## Realistic income (my judgment; no sales data exists yet)

- Books 1-3 as they stand: most likely **$0-20 in total over the first 90 days**. They were made before any research, have no reviews and no ads.
- If the research gate finds verified GO niches and 10-15 books are built there at 50 pictures and $9.99: a plausible outcome is a few books selling 5-20 copies a month, roughly **$30-150 a month** after 6-12 months. Many portfolios of this kind stay near zero. Seasonal titles can spike and then stop.
- $300 a month needs about 96 sales a month at $9.99. That is a good outcome, not the expected one.
- Cost side is tiny (about $0.35 of images per book), so the real cost is the owner's time and the proof copies. The kill rule exists so that neither is spent on niches that do not sell.
