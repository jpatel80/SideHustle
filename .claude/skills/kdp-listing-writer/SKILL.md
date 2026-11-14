---
name: kdp-listing-writer
description: Use when writing or revising the KDP listing for a book in this repo: title, subtitle, description, 7 keyword slots, categories, age range, pricing notes and the AI-disclosure answers. Produces books/NNN-slug/listing.md for the owner to paste into KDP.
---

# KDP listing writer

Read CLAUDE.md first. The listing is **generated**: edit the listing fields in `books/NNN-slug/book.json`, then run `python3 scripts/book_factory.py kit books/NNN-slug` (or `finish`), which writes `listing.md` and `final/UPLOAD_KIT.md`. Never edit `listing.md` by hand. The owner pastes it into KDP; you never log in to KDP.

## Fields in book.json
- **title / subtitle**: plain and accurate; the subtitle states the picture count and who it is for. The count must match the pages and the cover badge (the factory checks).
- **author**: pen name only (Wren Ashby for kids; the adult pen name for adult books). **imprint**: Little Fox Paper Co.
- **description** (HTML, at most 4000 characters): what is inside, who it suits, the black-and-white note, the AI sentence. No educational or health claims.
- **keywords**: exactly 7, each 50 characters or fewer, taken from real search suggestions (`research/autocomplete/*.json`) and true of the book. No brands, no competitor or author names.
- **categories**: up to three paths; mark them [verify] until the owner confirms them in the form.
- **price_usd**: use `scripts/kdp_pricing.py`. Amazon.com pays 50% below $9.99 and 60% from $9.99.
- **reading_age** for kids' books; **notes** for anything the owner must know.

## Rules
Mark every unverified claim **[verify]**. `book_factory.py check` must pass. If a KDP form field is unclear, say so in `notes` rather than guess.
