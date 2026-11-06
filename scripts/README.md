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

Constants marked VERIFY in the script (gutter table, spine thickness, minimum pages, barcode
area) come from KDP help pages and secondary guides. Re-check them against KDP's current
pages before publishing, and always review the file in KDP's online previewer.

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
  --model <winner> --style kids --budget 4 --dry-run --hint-price
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
