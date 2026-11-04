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
