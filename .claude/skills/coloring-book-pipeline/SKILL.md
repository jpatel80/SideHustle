---
name: coloring-book-pipeline
description: Use when the user wants to create, continue or QA a coloring book for KDP in this repo: from page ideas to generated images, QA, interior PDF and cover size. Triggers on "make a coloring book", "generate the pages", "build the interior", "next book", "bake-off".
---

# Coloring book pipeline (Little Fox Paper Co)

Read CLAUDE.md first; its rules override anything here.

## Steps
1. **Brief** `books/NNN-slug/brief.md`: audience, theme, 25-35 page ideas, style rules, banned list (copyrighted characters, brands, celebrities). Page ideas are plain English, one per line, in `subjects.txt`. Keep them simple and varied; closed shapes, one clear subject.
2. **Model choice** (first book only, or when switching): `python3 scripts/generate_images.py bakeoff prompts/bakeoff_subjects.txt --models <list> --count 5 --quality low --budget 3 -o out/bakeoff`; open the contact sheets; judge line quality, not just cost.
3. **Generate**: dry-run first (`--dry-run --hint-price`), then `generate ... --budget <cap>`. Re-running resumes; delete a bad image and re-run to regenerate it. Use `--variants 2` only when rerolls would cost more.
4. **QA**: `python3 scripts/build_interior.py qa books/NNN-slug/pages`, then view every page. Reject: gray shading or filled black areas, open or broken outlines, stray text or letters, extra limbs/odd anatomy, near-duplicates, anything resembling a copyrighted character.
5. **Build**: `python3 scripts/build_interior.py build <pages> -o <interior.pdf> --title ... --subtitle ... --author "Wren Ashby"`. Needs >= 24 pages total (KDP min, **[verify]**). Check the JSON summary has no problems and fonts are embedded.
6. **Cover**: `python3 scripts/build_interior.py cover-dims --pages <final page count> --trim 8.5x11`; then make the cover (see `scripts/make_cover.py` once it exists). Verify against KDP's cover calculator **[verify]**.
7. **Listing**: use the `kdp-listing-writer` skill, save to `listing.md`.
8. **Hand off**: list files, page count, spend (ledger.jsonl), open questions. The owner uploads and publishes.

## Style defaults (kids, ages 4-8)
Very bold uniform outlines, large simple shapes, pure white background, no shading/gray/fills/text/borders, subject centered with margin, friendly look. Adult books: fine detailed patterns, still no gray or solid fills.
