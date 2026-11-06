#!/usr/bin/env python3
"""Archive a finished book into books/NNN-slug/final/ so it can be committed to git and found later.

Copies interior.pdf, cover.pdf and the cover preview, stores the page images as optimized PNGs
(grayscale when R, G and B differ by at most 16 levels, i.e. line art with faint model noise; color pages stay RGB), copies the cost ledger,
and writes final/MANIFEST.md with page counts, file sizes, SHA-256 checksums and total spend.

Usage:
  python3 scripts/archive_book.py books/001-cozy-winter-animals

The working files (pages/, interior.pdf, cover.pdf) stay where they are; final/ is the committed copy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops

PAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
NEAR_GRAY = 16  # max R/G/B difference still treated as gray (image models leave faint chroma noise on line art)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_gray(im: Image.Image, tol: int = NEAR_GRAY) -> bool:
    """True when R, G and B differ by at most `tol` everywhere. build_interior.py converts every page to
    luminance anyway, so storing such pages as grayscale loses nothing that reaches the PDF."""
    if im.mode in ("L", "1"):
        return True
    r, g, b = im.convert("RGB").split()
    worst = max(ImageChops.difference(r, g).getextrema()[1], ImageChops.difference(g, b).getextrema()[1])
    return worst <= tol


def store_page(src: Path, dst: Path) -> dict:
    """Write src as an optimized PNG at dst (grayscale if near-gray, else RGB). Returns before/after info."""
    im = Image.open(src)
    im.load()
    gray = is_gray(im)
    out = im.convert("L") if gray else im.convert("RGB")
    out.save(dst, format="PNG", optimize=True)
    return {"file": dst.name, "gray": gray, "src_bytes": src.stat().st_size, "dst_bytes": dst.stat().st_size,
            "size_px": list(out.size)}


def ledger_total(*paths: Path) -> tuple[int, float]:
    n, total = 0, 0.0
    for p in paths:
        if p.is_file():
            for line in p.read_text().splitlines():
                if line.strip():
                    row = json.loads(line)
                    n += 1
                    total += float(row.get("cost_usd") or 0)
    return n, total


def archive(book: Path, force: bool = False) -> dict:
    book = Path(book)
    pages_dir = book / "pages"
    interior, cover = book / "interior.pdf", book / "cover.pdf"
    missing = [str(p) for p in (pages_dir, interior, cover) if not p.exists()]
    if missing:
        raise SystemExit(f"cannot archive {book}: missing {', '.join(missing)}")
    final = book / "final"
    if final.exists() and not force:
        shutil.rmtree(final)  # final/ is generated output: always rebuilt from the working files
    (final / "pages").mkdir(parents=True, exist_ok=True)

    images = sorted(p for p in pages_dir.iterdir() if p.suffix.lower() in PAGE_EXTS)
    page_info = [store_page(p, final / "pages" / (p.stem + ".png")) for p in images]
    for src in (interior, cover):
        shutil.copy2(src, final / src.name)
    preview = book / "cover.png"
    if preview.is_file():
        shutil.copy2(preview, final / "cover_preview.png")
    ledger = pages_dir / "ledger.jsonl"
    if ledger.is_file():
        shutil.copy2(ledger, final / "ledger.jsonl")
    n_req, spend = ledger_total(ledger)

    try:
        from pypdf import PdfReader

        n_pages = len(PdfReader(str(final / "interior.pdf")).pages)
    except Exception:  # pypdf missing or unreadable PDF: say so instead of guessing
        n_pages = None

    files = sorted(p for p in final.rglob("*") if p.is_file() and p.name != "MANIFEST.md")
    total_bytes = sum(p.stat().st_size for p in files)
    lines = [
        f"# Final files: {book.name}",
        "",
        f"- Interior PDF pages: {n_pages if n_pages is not None else 'unknown (pypdf not available)'}",
        f"- Page images: {len(page_info)} (optimized PNG; stored as grayscale: {sum(1 for i in page_info if i['gray'])}, same luminance the interior builder uses)",
        f"- Image requests in ledger: {n_req}, total spend this book: ${spend:.4f}",
        f"- Total size of final/: {total_bytes / 1e6:.1f} MB",
        "",
        "Upload to KDP: `interior.pdf` (manuscript) and `cover.pdf` (cover). Listing text: `../listing.md`.",
        "",
        "| file | bytes | sha256 |",
        "|---|---|---|",
    ]
    for p in files:
        lines.append(f"| {p.relative_to(final)} | {p.stat().st_size} | {sha256(p)[:16]}... |")
    (final / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"final": str(final), "pages": len(page_info), "interior_pages": n_pages, "bytes": total_bytes,
            "spend_usd": round(spend, 4)}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("book", help="books/NNN-slug folder with pages/, interior.pdf and cover.pdf")
    a = p.parse_args(argv)
    info = archive(Path(a.book))
    print(json.dumps(info, indent=2))
    print(f"\nNext: git add {info['final']} && git commit, then push the branch.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
