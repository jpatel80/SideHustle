---
name: coloring-book-pipeline
description: Use when the user wants to create, continue or QA a coloring book for KDP in this repo: from page ideas to generated images, QA, interior PDF and cover size. Triggers on "make a coloring book", "generate the pages", "build the interior", "next book", "bake-off".
---

# Coloring book pipeline (Little Fox Paper Co)

Read CLAUDE.md first; its rules override anything here. MEMORY.md has the current state; docs/AUTOPILOT.md the whole loop.

## Steps
1. **Niche**: build only for a keyword with a GO verdict in `research/niches_*.md` (`scripts/research_niches.py`). Without one, say so and ask the owner; never present an unverified niche as researched.
2. **Brief**: `books/NNN-slug/brief.md` (audience, theme, banned list), `subjects.txt` (50 page ideas, plain English, one per line, none repeated from another book) and `book.json` (copy `books/book.template.json`). Kids: Wren Ashby. Adults: the adult pen name and `"style_file": "prompts/style_adult_clean.txt"`.
3. **Check** (free): `python3 scripts/book_factory.py check books/NNN-slug`. Fix every problem; read every warning.
4. **Pages** (paid, capped): `python3 scripts/book_factory.py pages books/NNN-slug --generate`. Then open every contact sheet in `books/NNN-slug/review/`. Reject: gray shading or filled black areas, open or broken outlines, stray text, odd anatomy, a frame around the page, near-duplicates, anything resembling a copyrighted character, line weight that differs from the rest. To redo a page delete its file and run the command again.
5. **Finish**: `python3 scripts/book_factory.py finish books/NNN-slug --reviewed` builds the interior, cover, `listing.md` (upload kit) and `final/`. Look at the full cover and at page 1-3 and the last leaf of the interior.
6. **Hand off**: commit `books/NNN-slug/` and push; send the cover preview, contact sheets, interior.pdf, cover.pdf and listing.md with SendUserFile; report page count, spend (`book_factory.py spend books`) and open questions. The owner uploads and publishes.

## Style notes
Kids: very bold uniform outlines, one clear subject, no shading/fills/text/borders. Adults: bold clean lines, no hatching or texture marks (fine detail from the current model prints crackly). Default 50 pictures, $9.99.
