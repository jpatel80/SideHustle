# TODO: Little Fox Paper Co setup tracker

Brand / imprint: **Little Fox Paper Co** (never "Little Fox" alone). Author (pen name): **Wren Ashby** (backup: Hazel Larkin).
Last updated: 2026-11-06 (books 1-3 built). Tick boxes as you go; Claude updates the Claude sections.

## A. You (human-only steps)

Do these in order. Section A1-A3 can be done any time before the new session; none needs money except the OpenRouter credit and domains.

### A1. Name and brand (about 30 minutes)
- [ ] Search **Wren Ashby** in Amazon Books and the Kindle store. If an author with that exact name has books, switch to **Hazel Larkin** (and search it too). Also Google it.
- [ ] Register **littlefoxpaper.com** and **littlefoxpaper.co** (both looked unregistered on 2026-11-05; first come, first served). Check the price at checkout.
- [ ] Claim the Etsy shop name and Instagram / Pinterest / TikTok handles (try `littlefoxpaperco`).
- [ ] Decide: one pen name for kids and adult books, or two. (Default: one, add a second later if the mix feels off.)

### A2. KDP account (20-30 minutes, free)
- [ ] Create or sign in to one Amazon login at kdp.amazon.com; turn on two-step verification.
- [ ] *Account > Your Account*: legal name, address, phone.
- [ ] *Getting Paid*: bank account (account holder name must match the bank).
- [ ] Complete the **tax interview** (US: W-9; non-US: W-8BEN). Legal name and tax ID, never the pen name.
- [ ] Complete identity verification if KDP shows the banner.
- [ ] Optional but recommended: email KDP Support: "Can I use a brand name as the author name?" and note the answer in PLAN.md. Reason: the author name cannot be changed after a book is published.
- [ ] Do not publish anything yet.

### A3. Image generation (10 minutes, $20)
- [ ] Create an OpenRouter account, add **$20** credit, turn auto-recharge **off**.
- [ ] Create an API key with a **credit limit** if the option exists (suggest $20).
- [ ] In the cloud environment settings (environment menu in the session title bar > Edit) add the key as an environment variable named **`OPENROUTER_API_KEY`**. Never paste it in chat or commit it.
- [ ] In the same settings, confirm `openrouter.ai` is in the allowed network domains (it was reachable on 2026-11-05).

### A4. Start the next session
- [ ] When A1-A3 are done, start a **new session** on this repo and paste the prompt in `NEW_SESSION_PROMPT.md`.

### A5. After the first draft is ready (the new session will tell you)
- [ ] Review the generated pages, the interior PDF and the cover (`books/001-cozy-winter-animals/`); reject any you don't like.
- [ ] Upload book 1 to KDP (about 10-15 min; Claude prepares every field in `books/001-cozy-winter-animals/listing.md`). Check the file in KDP's online previewer.
- [ ] Select **Yes** for AI-generated images in the KDP form. Be honest in every field.
- [ ] Optional: order one proof copy of the best book (a few dollars plus shipping).
- [ ] Press Publish yourself.

### A6. Later (only after Gate 1 below)
- [ ] Create Etsy and Printify accounts (free) for the tee track.
- [ ] Before merchandise: short consult with a trademark attorney about LITTLE FOX.
- [ ] Consider your own ISBN only if you want a visible Publisher name (reportedly required for that; costs money; verify).

## B. Claude (status)

### Done
- [x] Research on KDP, AI disclosure, economics, tools (PLAN.md)
- [x] `scripts/build_interior.py`: QA, KDP interior PDF builder, cover dimensions (13 tests)
- [x] `scripts/generate_images.py`: OpenRouter image generator, hard budget, resume, bake-off (14 tests, live price lookup verified)
- [x] USPTO checks and name decision (research/)
- [x] Pen-name shortlist; **Wren Ashby** chosen
- [x] Project rules (`CLAUDE.md`), summary of agreements (`MEMORY.md`, also saved to the memory tool) and two project skills (`.claude/skills/`)
- [x] Book 1 brief, 30 page ideas, draft listing (`books/001-cozy-winter-animals/`)

### Books 1-3 (built 2026-11-06; finished files are committed under `books/NNN-slug/final/`)
- [x] **Book 1** Cozy Winter Animals (kids 4-8, 30 pictures, 64 pages): approved by the owner
- [x] **Book 2** Cozy Cottage Coloring Book for Adults (40 pictures, 84 pages, garden-theme cover): built, **waiting for owner review**
- [x] **Book 3** Happy Ocean Animals Coloring Book (kids 3-6, extra simple, 30 pictures, 64 pages, ocean-theme cover): built, **waiting for owner review**
- [x] Model: `openai/gpt-image-2` at low quality for all three (adult also tested at medium and high: thinner lines, 8x and 33x the price)
- [x] KDP constants verified (gutter, bleed, spine thickness, 24-page minimum, barcode); spine text needs 80+ pages **and** a spine wide enough for readable type (book 2's 0.19 in spine is left blank)
- [x] Scripts: `make_cover.py` + `cover_fun.py` (fun covers, themes winter/ocean/garden), `archive_book.py`; 59 tests
- [ ] **Owner review of books 2 and 3** (see A5): covers, contact sheets, listings; decide pen name for the adult book (default: same Wren Ashby)
- [ ] Optional script fix: per-model aspect-ratio fallback in `generate_images.py` (Krea)
- [ ] Stop and ask before any further books (Gate 1 needs the owner to publish and see the books through KDP review)

### Needs book 1 live and some sales data
- [ ] Gate 2 review at ~day 90 (see PLAN.md)
- [ ] Tee track: trend research, designs, Etsy/Printify listings

## C. Gates (from PLAN.md)
- **Gate 1:** 3 books live, no policy flags, workflow tolerable.
- **Gate 2 (~day 90):** any title selling consistently? If ~15-20 books produce ~no sales, stop or change direction; add no money.
- **Gate T1 (~day 60 of tees):** 15 listings live, any sale at all?

## D. Spending caps
OpenRouter credit $20 total. Bake-off <= $3. Book 1 <= $4. **Spent so far: about $2.21 of $20** (ledger files): bake-off $0.68, quality tests for books 2 and 3 $0.77 (the $0.59 was a three-image test at high quality), book 1 $0.33, book 2 $0.24, book 3 $0.20. Caps per book ($4) were not approached. No ads, no paid tools, no domains beyond the two above until Gate 2.

## E. Time-sensitive note
Book 1 is winter-themed. Holiday gift demand is strongest in the weeks before late December, and KDP review takes days (reported up to ~72 hours for eBooks and longer for paperbacks; verify). The later it goes live, the more it relies on year-round "winter" demand. Not a reason to rush quality.
