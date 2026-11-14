# Scripts

Normal use is the **book factory**; the other scripts are its parts and can be run alone.

```bash
# 0. research (free): what do shoppers type, and can a new book compete?
python3 scripts/research_niches.py harvest --seeds research/seeds.txt --expand -o research/autocomplete/$(date +%F).json
python3 scripts/research_niches.py worksheet "bold and easy coloring book for adults"   # fill the CSV from Amazon's results
python3 scripts/research_niches.py rank research/autocomplete/<date>.json -o research/niches_<date>.md

# 1. a book: copy books/book.template.json to books/NNN-slug/book.json, write subjects.txt (50 page ideas)
python3 scripts/book_factory.py check  books/NNN-slug             # free
python3 scripts/book_factory.py pages  books/NNN-slug --generate  # paid, capped; then LOOK at books/NNN-slug/review/
python3 scripts/book_factory.py finish books/NNN-slug --reviewed  # interior.pdf, cover.pdf, listing.md, final/
python3 scripts/book_factory.py spend  books                      # total spend against the $25 cap

# 2. money
python3 scripts/kdp_pricing.py --pages 106 --target 300
python3 scripts/sales_tracker.py                                   # reads tracking/kdp_reports/, writes tracking/REPORT.md
```

To redo a page: delete its file in `books/NNN-slug/pages/` and run `pages --generate` again. If the page idea
changed, delete the old file too (the file name comes from the idea). In a new container `pages` restores the
working folder from `final/` first (`archive_book.py --restore`).

Changes on 2026-11-14: `generate` needs `--budget` and the cap counts earlier runs in the same folder;
`build` renders art at 600 DPI with a 0.5 in gutter, a picture on the title page and a color test page on the
last leaf (`--no-test-page`, `--title-art 0`, `--display-font none` switch these off); `qa` takes
`--style kids|adult` and `--against <other books' page folders>`; the cover PDF contains no fonts.

The sections below describe the individual scripts.

# scripts/build_interior.py

Turns a folder of generated images into a KDP-ready coloring-book interior.

```bash
pip install -r requirements.txt

# 1. mechanical QA (gray shading, solid fills, empty pages, duplicates, low-res)
python3 scripts/build_interior.py qa books/<slug>/pages

# 2. build the interior (art on right-hand pages, blank backs, embedded fonts)
python3 scripts/build_interior.py build books/<slug>/pages \
  -o books/<slug>/interior.pdf --title "Garden Friends" \
  --subtitle "A Coloring Book for Kids" --author "<pen name>"

# 3. cover size for the page count you ended up with
python3 scripts/build_interior.py cover-dims --pages 52 --trim 8.5x11
```

Name images so they sort in book order (`01.png`, `02.png`, ...). Default trim is 8.5x11, no bleed.
Use `--bleed` only if art must run to the page edge.

The KDP constants in the script (gutter table, spine thickness, minimum pages, barcode area) were checked
against KDP help pages on 2026-11-06 and 2026-11-14. Always review the file in KDP's online previewer.

Tests: `python3 -m unittest discover -s tests -v`

# scripts/generate_images.py

Generates page art through OpenRouter's Image API. Key comes from the `OPENROUTER_API_KEY`
environment variable only (set it in the cloud environment's settings; never in chat or the repo).

```bash
# see per-image prices (public, no key)
python3 scripts/generate_images.py models

# 1. model bake-off: same 5 subjects through several models, $3 total cap
python3 scripts/generate_images.py bakeoff prompts/bakeoff_subjects.txt \
  --models recraft/recraft-v4.1,qwen/qwen-image-3,krea/krea-2-medium,bytedance-seed/seedream-5-0-lite,openai/gpt-image-2 \
  --count 5 --quality low --budget 3 -o out/bakeoff
#    -> out/bakeoff/contact_<model>.png (look at them) and bakeoff_report.md

# 2. a real book: preview the plan, then generate with a hard cap
python3 scripts/generate_images.py generate books/<slug>/subjects.txt -o books/<slug>/pages \
  --model <winner> --style kids --dry-run --hint-price
python3 scripts/generate_images.py generate books/<slug>/subjects.txt -o books/<slug>/pages \
  --model <winner> --style kids --budget 4
```

Re-running a command resumes: finished images are skipped. Every request's real cost is appended
to `<out>/ledger.jsonl`. `--budget` stops the run before it would overspend. Vector (SVG) models save
`.svg` files, which need rasterizing before `build_interior.py` can use them.

Typical flow per book: generate -> `build_interior.py qa` -> look at flagged pages, regenerate
the bad ones (delete the file, re-run) -> `build_interior.py build`.

# scripts/make_cover.py

Builds the KDP wrap-around cover PDF (back + spine + front, 300 DPI, bleed included) from one
page image of the book, plus PNG previews (flat and with trim/spine/safe/barcode guides). Uses
the KDP constants from `build_interior.py`; the spine gets text only at 80+ pages; the back keeps
a blank white 2 x 1.2 in barcode area.

```bash
python3 scripts/make_cover.py books/<slug>/pages/01_*.png -o books/<slug>/cover.pdf \
  --title "..." --subtitle "..." --author "<pen name>" --imprint "Little Fox Paper Co" \
  --pages 64 --blurb "line one|line two"
```

Styles: `--style fun` (default) draws a gradient with sunburst, snowflakes and confetti, a bouncy rainbow
title (Chewy font in `assets/fonts/`, Apache 2.0), a tilted framed art panel, a ribbon for the subtitle, an
optional starburst `--badge "30|BIG PICTURES|TO COLOR!"` and round colored `--stickers <page images>` (first 3 on
the front, next 2 on the back). `--style plain` is the simple blue cover. Helpers live in `scripts/cover_fun.py`.

`--colored-half` fills the enclosed regions of the front art with crayon colors on one side of a scribbled edge and draws a crayon at the edge ("someone is coloring it"); the lines are untouched and `--seed` changes the color choices. Needs scipy.

Interior flag added: `build_interior.py build ... --imprint "Little Fox Paper Co"` prints the imprint
on the title and copyright pages.
