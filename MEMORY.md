# Project memory: the single current-state file (updated 2026-11-14)

Read this first, then CLAUDE.md (rules) and TODO.md (who does what next). `docs/AUTOPILOT.md` explains how the system runs with little owner time. PLAN.md is history: where it differs from this file, this file wins.

## What this is
- A low-capital side project: **coloring books on Amazon KDP** under the imprint **Little Fox Paper Co**. Claude prepares everything; **the owner uploads and publishes** (Claude never logs in to KDP).
- Goal: income toward monthly bills with very little owner time. Honest expectation: most titles earn little; see "Money" below.

## Status (2026-11-14)
| Book | Audience | Pictures / pages | Author on the book | List price | State |
|---|---|---|---|---|---|
| 001 Cozy Winter Animals Coloring Book | kids 3-6 | 30 / 66 | Wren Ashby | $7.99 | Rebuilt after the audit (2 pages rerolled). Ready to upload once the pen name is checked. The owner approved the earlier version; the changes need a quick look. |
| 002 Cozy Cottage Coloring Book for Adults | adults | 50 / 106 | Clara Whitcombe (**placeholder**) | $9.99 | Regenerated in a bold, clean style (the first version printed crackly). Waits for the owner's review, the adult pen name and a proof copy. |
| 003 Happy Ocean Animals Coloring Book | toddlers 1-4 | 30 / 66 | Wren Ashby | $6.99 | Rebuilt after the audit (5 pages replaced). Waits for the owner's review. |

Nothing is published. No sales data exists. The three niches were chosen before any research and are unverified.

## Decisions in force
- **Brand: Little Fox Paper Co** (owner re-confirmed 2026-11-14, accepting the overlap with other "Little Fox" marks). Always the full name. Imprint only: cover, title page, copyright page. Never in the KDP Author field. No educational, songs, story-app or English-learning positioning. **No domains or handles are bought until a book sells.**
- **Pen names:** Wren Ashby = kids' books only (fallback Hazel Larkin). Adult books get a second pen name; three proposals and the Amazon check are in `research/pen_names.md`. Book 2 carries proposal 1 as a marked placeholder. No bio credentials, no AI headshot.
- **Budget: $25 total** for image generation and proof copies together (raised from $20 on 2026-11-14). $4 per book for images. **No ads for now** (an ads test is designed in `docs/AUTOPILOT.md` but disabled). Spent: **$2.80** (books $1.35, bake-off $0.68, quality tests $0.77). `python3 scripts/book_factory.py spend books` prints the current total.
- **Research:** free sources only for now (Amazon's public search-suggestion endpoint, web search, KDP help pages). Amazon pages are not scraped. If the owner links their own browser, competitor data goes into `research/competitors/*.csv` (columns in `scripts/research_niches.py`).
- **AI disclosure:** always Yes in the KDP form; the copyright page says the illustrations were generated with AI image tools and claims only selection, arrangement and design.
- **Branches:** work on the session branch; merge into `main` only what the owner approved.

## Money (verified on KDP help pages 2026-11-14)
- Paperback royalty on Amazon.com = rate x list price - printing cost. **Rate: 50% up to $9.98, 60% from $9.99.**
- Printing cost, black ink, 8.5 x 11: **$2.84 flat for 24-110 pages**; above 110 pages $1.00 + $0.017 per page.
- So: $6.99 earns $0.66, $7.99 earns $1.16, $8.99 earns $1.66, **$9.99 earns $3.15**. `scripts/kdp_pricing.py` does the sums.
- 50 pictures (104-106 pages) cost the same to print as 30. New books default to 50 pictures and $9.99.
- $300 a month needs about 96 sales a month at $9.99, or about 259 at $7.99.
- Realistic outlook (my judgment, not data): the first three books most likely earn $0-20 in total in their first 90 days without ads or reviews. A portfolio that works takes months and may not happen. The kill rule in `scripts/sales_tracker.py` stops spending when nothing sells.

## How a book is made now
1. `scripts/research_niches.py` proposes niches; a niche is built only with a **GO** from a filled competitor worksheet.
2. `books/NNN-slug/book.json` (copy `books/book.template.json`) + `subjects.txt` (50 page ideas).
3. `scripts/book_factory.py check | pages --generate | finish --reviewed`: pages, QA, contact sheets, interior, cover, `listing.md` (the owner's upload kit), archive in `final/`.
4. Claude looks at every contact sheet before `finish`; the owner gets the cover, contact sheets, PDFs and the kit via SendUserFile.
5. Owner uploads with the kit (about 10 minutes), orders a proof for a new style, publishes, tells Claude the date (`published` in book.json).
6. Monthly: owner drops the KDP report in `tracking/kdp_reports/`; `scripts/sales_tracker.py` writes `tracking/REPORT.md` with a decision per book.

## Technical facts
- Model: `openai/gpt-image-2` at `--quality low` through OpenRouter, about $0.006 per image, 1152 x 1536 px. Kids: built-in `kids` style. Adults: `prompts/style_adult_clean.txt` (bold clean lines, no hatching). Finely detailed adult art from this model prints crackly: do not use the old `adult` style for print.
- Interior: 8.5 x 11, no bleed, white paper, black ink, art at 600 DPI on right-hand pages with blank backs, 0.5 in gutter, title page with a picture, "belongs to" page, color test page on the last leaf, fonts embedded.
- Cover: `make_cover.py` fun style (owner-approved family), RGB image at 300 DPI, no fonts in the PDF, blank barcode box, spine text only when the spine leaves 0.125 in for type (about 111+ pages).
- KDP limits checked: 24-page minimum, gutter 0.375 in up to 150 pages, spine 0.002252 in per page (white), spine text needs 79+ pages, cover wants embedded fonts and 300 DPI, three new titles per day per account.
- Generator: `--budget` is required and cumulative per book folder (ledger); prompts are logged. `archive_book.py --restore` rebuilds `pages/` from `final/` in a fresh container.
- Environment: cloud container, reclaimed between sessions. `OPENROUTER_API_KEY` is an environment variable (never printed). `scripts/setup_env.sh` is the setup script to save on the environment. 109 tests: `python3 -m unittest discover -s tests` (about 6 minutes).
- Repo size: `final/` folders hold PDFs and PNGs (about 125 MB for three books). Move to Git LFS or release assets before book 10.

## Open risks
- Niches are unverified; all three books may sell nothing.
- Books 1 and 3 have 30 pictures: thin against competitors with 50-100.
- The adult book uses the kids' cover family (current rule); an adult-style cover is recommended.
- Trademark overlap of "Little Fox" (accepted by the owner). Attorney before merchandise.
- AI images may not be protected by copyright in the US; competitors can copy pages.
- One KDP account: a termination is account-wide. Never open a second account.
