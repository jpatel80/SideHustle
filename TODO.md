# TODO: Little Fox Paper Co

Last updated: 2026-11-14. Current state and numbers are in MEMORY.md; this file is only "who does what next".

## A. Owner (in this order)

### A1. Before any upload (about 30 minutes, once)
- [ ] **Pen-name search on Amazon** (`research/pen_names.md` has the exact searches): confirm *Wren Ashby* is free, and choose the adult pen name (Clara Whitcombe / Marian Thistlewood / Nell Hartwell). The author name cannot be changed after publishing.
- [ ] **KDP account:** one Amazon login at kdp.amazon.com, two-step verification on, legal name and address, bank account.
- [ ] **Tax interview** in KDP (legal name and tax ID, never the pen name). US person: W-9. Outside the US: W-8BEN; enter your tax ID so a treaty rate can apply, then read the withholding rate KDP shows in your tax profile and tell Claude the figure. Without a treaty claim, US-source royalties are withheld at 30% **[verify for your country on the IRS treaty table]**.
- [ ] Tell Claude your country of tax residence (it changes the income sums).
- [ ] Never open a second KDP account.

### A2. Review the rebuilt books (about 15 minutes)
- [ ] Book 1 *Cozy Winter Animals*: 2 pages replaced (moose, picnic), new title / name / test pages, cover subtitle now "Ages 3-6". Yes or no.
- [ ] Book 3 *Happy Ocean Animals*: 5 pages replaced, subtitle now "for Toddlers Ages 1-4". Yes or no.
- [ ] Book 2 *Cozy Cottage*: all 50 pages are new (bold, clean style). Yes or no; and say whether you want an adult-style cover (recommended, needs a rule change in CLAUDE.md).
- [ ] Decide: extend books 1 and 3 from 30 to 50 pictures (about $0.15 each, lets them sell at $9.99 for a $3.15 royalty instead of $1.16 / $0.66)?

### A3. Upload (about 10 minutes per book)
- [ ] Follow `books/NNN-slug/listing.md` (the upload kit) field by field. Answer **Yes** to AI-generated content.
- [ ] Order **one proof copy** per style before publishing (book 1 or 3 for the kids' style, book 2 for the adult style). Proofs count toward the $25 total.
- [ ] Press Publish yourself. Tell Claude the date for each book.

### A4. Monthly (about 5 minutes)
- [ ] Download the KDP royalties report into `tracking/kdp_reports/` (or upload it in a session); Claude runs the tracker and sends `tracking/REPORT.md`.

### A5. Research help (about 10 minutes per keyword, until a browser is linked)
- [ ] Fill competitor worksheets in `research/competitors/` for the keywords Claude proposes (first six are named in `docs/AUTOPILOT.md`). Columns are in the file.

### A6. Things only you can check (about 10 minutes in total)
- [ ] Amazon search "bold and easy coloring book for adults": are the first 10 results mostly 50 pictures at $7.99-$9.99? (Web retailers suggest so.)
- [ ] Amazon search "coloring book for toddlers 1-3": page counts and prices of the first 10 (web retailers show about 100 pictures at $4.39-$6.99, which would make book 3 poor value).
- [ ] In the KDP form: does the AI question offer the answers written in the kit? Is the "low-content" box where the kit says?
- [ ] KDP > Reports: the exact name of the royalties download, so the tracker instructions can be corrected.

### A7. Settings
- [ ] GitHub: make `main` the default branch (Settings > Branches).
- [ ] Cloud environment: save `scripts/setup_env.sh` as the setup script (or approve it when Claude proposes it).

## B. Claude

### Done on 2026-11-14 (audit fixes)
- [x] Royalty maths corrected everywhere; `scripts/kdp_pricing.py`
- [x] Cover PDFs no longer declare an un-embedded font
- [x] Copyright page claims only selection, arrangement and design; says "generated with AI image tools"
- [x] Interior: picture on the title page, framed "belongs to" page, color test page, 0.5 in gutter, 600 DPI art
- [x] QA recalibrated (no more 100% false alarms); new checks: crackly detail, line weight, cut-off art, repeats across books
- [x] Generator: `--budget` required and cumulative, missing costs counted, prompts logged
- [x] Book 2 regenerated (50 bold clean pages); books 1 and 3 weak or repeated pages replaced; age labels corrected
- [x] Research gate, book factory, upload kits, sales tracker, autopilot design
- [x] MEMORY.md rewritten as the single current-state file; wrong Author-field instructions struck

### Next (waiting for the owner)
- [ ] Apply the chosen adult pen name to book 2 and rebuild
- [ ] If approved: extend books 1 and 3 to 50 pictures; adult cover style
- [ ] After approval: merge into `main`
- [ ] Rank niches once competitor worksheets exist; propose the next batch (stop for approval first)
- [ ] Move `final/` binaries to Git LFS or release assets before book 10
- [ ] A+ content image set and Author Central text, once a book is live

## C. Gates
- **Gate 1:** books live, no policy flags, proof copies look right.
- **Per book:** kill rule in `scripts/sales_tracker.py` (decide at day 60).
- **Gate 2 (day 90 after the first book):** nothing selling 8+ copies a month means no more money.
- Tee / merchandise track: parked until a book sells; trademark attorney first.

## D. Spending
Total cap **$25** for images and proof copies. Spent **$2.80**: book 1 $0.34, book 2 $0.78 (first version $0.24, print tests $0.21, new pages $0.34), book 3 $0.23, bake-off $0.68, quality tests $0.77. No ads, no domains, no paid tools.
