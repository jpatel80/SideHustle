#!/usr/bin/env python3
"""KDP coloring-book interior toolkit.

Subcommands
-----------
qa          Check a folder of generated images for common problems
            (gray shading, solid fills, near-empty pages, duplicates, low resolution).
build       Clean the images to pure black-and-white at 300 DPI and assemble a
            KDP-ready interior PDF (uniform page size, embedded fonts, gutter margins
            chosen from the final page count, optional bleed, blank backs).
cover-dims  Compute spine width and full-cover dimensions for the cover file.

Dependencies: Pillow, numpy, reportlab (pypdf optional, used to validate the output).

KDP numbers baked in below (gutter table, spine thickness, bleed, minimum pages) come
from KDP help pages and secondary guides. They are marked VERIFY: re-check them against
KDP's current "Set trim size, bleed, and margins" and cover-calculator pages before
publishing, and adjust the constants if Amazon has changed them.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

DPI = 300
PT = 72.0
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# VERIFY against KDP: minimum inside (gutter) margin in inches by final page count.
GUTTER_TABLE = [(150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875)]
MIN_PAGES = 24  # VERIFY: smallest paperback page count KDP accepts.
MAX_PAGES = 828  # VERIFY: largest page count for the gutter table above.
BLEED_W = 0.125  # extra width for a full-bleed PDF (outer edge only)
BLEED_H = 0.25  # extra height for a full-bleed PDF (top + bottom)
# VERIFY: spine thickness per page, inches.
SPINE_PER_PAGE = {"white": 0.002252, "cream": 0.0025, "premium-color": 0.002347}
SPINE_TEXT_MIN_PAGES = 79  # VERIFY: spine text is only allowed from this page count.

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

# QA thresholds
GRAY_LO, GRAY_HI = 48, 208  # pixel values counted as "gray" (neither ink nor paper)
MAX_GRAY_RATIO = 0.12
MAX_INK_RATIO = 0.30
MIN_INK_RATIO = 0.01
MIN_SIDE_PX = 1200
DUP_HAMMING = 6


# ----------------------------------------------------------------------------- helpers
def natural_key(p: Path):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def list_images(folder: Path) -> list[Path]:
    files = [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS and p.is_file()]
    return sorted(files, key=natural_key)


def parse_trim(s: str) -> tuple[float, float]:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*", s)
    if not m:
        raise argparse.ArgumentTypeError(f"trim must look like 8.5x11, got {s!r}")
    return float(m.group(1)), float(m.group(2))


def gutter_for(pages: int) -> float:
    for limit, g in GUTTER_TABLE:
        if pages <= limit:
            return g
    raise ValueError(f"{pages} pages exceeds the {MAX_PAGES}-page limit")


def load_gray(path: Path) -> Image.Image:
    im = Image.open(path)
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA") or "transparency" in im.info:
        im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        im = bg
    return im.convert("L")


def otsu_threshold(arr: np.ndarray) -> int:
    hist = np.bincount(arr.ravel(), minlength=256).astype(float)
    total = hist.sum()
    levels = np.arange(256)
    cum = np.cumsum(hist)
    cum_sum = np.cumsum(hist * levels)
    w0 = cum
    w1 = total - cum
    mu0 = cum_sum / np.maximum(w0, 1)
    mu1 = (cum_sum[-1] - cum_sum) / np.maximum(w1, 1)
    between = w0 * w1 * (mu0 - mu1) ** 2
    return int(np.argmax(between))


def pick_threshold(arr: np.ndarray, setting: str) -> int:
    if setting == "auto":
        # Clamp: very low values eat thin lines, very high values fatten them.
        return int(min(max(otsu_threshold(arr), 110), 190))
    return int(setting)


def autocrop(gray: Image.Image, pad_frac: float = 0.02, ink_level: int = 200) -> Image.Image:
    a = np.asarray(gray)
    mask = a < ink_level
    rows = np.where(mask.sum(axis=1) >= 2)[0]
    cols = np.where(mask.sum(axis=0) >= 2)[0]
    if rows.size == 0 or cols.size == 0:
        return gray
    pad = int(pad_frac * max(gray.size))
    left = max(int(cols[0]) - pad, 0)
    right = min(int(cols[-1]) + pad + 1, gray.width)
    top = max(int(rows[0]) - pad, 0)
    bottom = min(int(rows[-1]) + pad + 1, gray.height)
    return gray.crop((left, top, right, bottom))


def dhash(gray: Image.Image) -> int:
    small = np.asarray(gray.resize((9, 8), Image.LANCZOS), dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# ----------------------------------------------------------------------------- qa
def analyse_image(path: Path) -> dict:
    gray = load_gray(path)
    w, h = gray.size
    probe = gray
    if max(w, h) > 1024:  # speed: statistics are scale-stable enough
        s = 1024 / max(w, h)
        probe = gray.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    a = np.asarray(probe)
    gray_ratio = float(((a > GRAY_LO) & (a < GRAY_HI)).mean())
    ink_ratio = float((a < 128).mean())
    ink = a < 128
    border = max(2, int(0.01 * max(a.shape)))
    touches = bool(
        ink[:border, :].any() or ink[-border:, :].any() or ink[:, :border].any() or ink[:, -border:].any()
    )
    flags = []
    if min(w, h) < MIN_SIDE_PX:
        flags.append(f"low resolution ({w}x{h}px; will be upscaled and look soft)")
    if gray_ratio > MAX_GRAY_RATIO:
        flags.append(f"gray shading/texture ({gray_ratio:.0%} mid-gray pixels)")
    if ink_ratio > MAX_INK_RATIO:
        flags.append(f"too much ink / solid fills ({ink_ratio:.0%} black)")
    if ink_ratio < MIN_INK_RATIO:
        flags.append(f"nearly empty page ({ink_ratio:.1%} black)")
    if touches:
        flags.append("artwork touches the image edge (may be cropped or feel cramped)")
    return {
        "file": path.name,
        "size_px": [w, h],
        "gray_ratio": round(gray_ratio, 4),
        "ink_ratio": round(ink_ratio, 4),
        "touches_edge": touches,
        "flags": flags,
        "_hash": dhash(probe),
    }


def run_qa(images: list[Path]) -> list[dict]:
    results = [analyse_image(p) for p in images]
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            if hamming(results[i]["_hash"], results[j]["_hash"]) <= DUP_HAMMING:
                for k, other in ((i, j), (j, i)):
                    results[k]["flags"].append(f"near-duplicate of {results[other]['file']}")
    for r in results:
        r.pop("_hash")
    return results


def cmd_qa(args) -> int:
    images = list_images(args.images)
    if not images:
        print(f"No images found in {args.images}", file=sys.stderr)
        return 2
    results = run_qa(images)
    bad = [r for r in results if r["flags"]]
    print(f"Checked {len(results)} images: {len(results) - len(bad)} clean, {len(bad)} flagged\n")
    for r in bad:
        print(f"  {r['file']}")
        for f in r["flags"]:
            print(f"    - {f}")
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))
        print(f"\nWrote {args.json}")
    print(
        "\nNote: this catches mechanical problems only. Open the pages and check for broken or open "
        "outlines, stray text, and odd anatomy before building."
    )
    return 1 if (bad and args.strict) else 0


# ----------------------------------------------------------------------------- build
def find_font(user: str | None, candidates: list[str], label: str) -> str | None:
    if user:
        if not Path(user).is_file():
            sys.exit(f"--font file not found: {user}")
        return user
    for c in candidates:
        if Path(c).is_file():
            return c
    return None


def register_fonts(font: str | None, bold: str | None) -> tuple[str, str]:
    reg = find_font(font, FONT_CANDIDATES, "font")
    if not reg:
        sys.exit(
            "No TrueType font found. KDP requires embedded fonts, so pass --font /path/to/font.ttf "
            "(any font you have the licence to embed)."
        )
    bld = find_font(bold, BOLD_CANDIDATES, "bold font") or reg
    pdfmetrics.registerFont(TTFont("BodyFont", reg))
    pdfmetrics.registerFont(TTFont("BoldFont", bld))
    return "BodyFont", "BoldFont"


def page_geometry(idx: int, trim_w: float, trim_h: float, bleed: bool, gutter: float, outer: float, vmargin: float):
    """Return (page_w_pt, page_h_pt, safe_rect_pt) for 1-based page idx.

    Odd pages are right-hand (recto): gutter on the left, bleed on the right.
    Even pages are left-hand (verso): gutter on the right, bleed on the left.
    """
    recto = idx % 2 == 1
    page_w = trim_w + (BLEED_W if bleed else 0)
    page_h = trim_h + (BLEED_H if bleed else 0)
    trim_x0 = 0.0 if (recto or not bleed) else BLEED_W
    trim_y0 = BLEED_H / 2 if bleed else 0.0
    if recto:
        left, right = trim_x0 + gutter, trim_x0 + trim_w - outer
    else:
        left, right = trim_x0 + outer, trim_x0 + trim_w - gutter
    bottom, top = trim_y0 + vmargin, trim_y0 + trim_h - vmargin
    return page_w * PT, page_h * PT, (left * PT, bottom * PT, right * PT, top * PT)


def draw_centered_text(c, text, font, size, y, page_w, max_w):
    for line in simpleSplit(text, font, size, max_w):
        c.setFont(font, size)
        c.drawCentredString(page_w / 2, y, line)
        y -= size * 1.25
    return y


def draw_text_page(c, kind, a, fonts, page_w, page_h, safe):
    body, bold = fonts
    left, bottom, right, top = safe
    cx_w = right - left
    c.setFillGray(0)
    if kind == "title":
        y = draw_centered_text(c, a.title, bold, 40, page_h * 0.62, page_w, cx_w)
        if a.subtitle:
            y = draw_centered_text(c, a.subtitle, body, 20, y - 10, page_w, cx_w)
        draw_centered_text(c, f"by {a.author}", body, 18, page_h * 0.18, page_w, cx_w)
    elif kind == "copyright":
        lines = [
            f"Copyright \u00a9 {a.year} {a.author}. All rights reserved.",
            "No part of this book may be reproduced in any form without written permission "
            "from the author, except for personal use of the pages for coloring.",
        ]
        if a.note:
            lines.append(a.note)
        y = top - 40
        for t in lines:
            y = draw_centered_text(c, t, body, 10, y, page_w, cx_w) - 8
    elif kind == "belongs":
        draw_centered_text(c, "This book belongs to", bold, 28, page_h * 0.58, page_w, cx_w)
        c.setLineWidth(1.2)
        c.line(left + cx_w * 0.15, page_h * 0.50, right - cx_w * 0.15, page_h * 0.50)


def build_plan(n_art: int, a) -> list[tuple[str, int | None]]:
    plan: list[tuple[str, int | None]] = [("title", None), ("copyright", None)]
    if a.belongs_to:
        plan += [("belongs", None), ("blank", None)]
    for i in range(n_art):
        plan.append(("art", i))
        if a.blank_backs:
            plan.append(("blank", None))
    return plan


def cmd_build(args) -> int:
    images = list_images(args.images)
    if not images:
        print(f"No images found in {args.images}", file=sys.stderr)
        return 2
    trim_w, trim_h = args.trim
    plan = build_plan(len(images), args)
    if len(plan) % 2:
        plan.append(("blank", None))
    if len(plan) < MIN_PAGES:
        if args.pad_to_min:
            while len(plan) < MIN_PAGES:
                plan.append(("blank", None))
        else:
            need = MIN_PAGES - len(plan)
            per_image = 2 if args.blank_backs else 1
            print(
                f"Only {len(plan)} pages; KDP needs at least {MIN_PAGES}. Add ~{-(-need // per_image)} more "
                "images, or pass --pad-to-min to pad with blank pages.",
                file=sys.stderr,
            )
            return 2
    if len(plan) > MAX_PAGES:
        print(f"{len(plan)} pages exceeds the {MAX_PAGES}-page limit.", file=sys.stderr)
        return 2

    n_pages = len(plan)
    gutter = max(gutter_for(n_pages), args.gutter or 0)
    fonts = register_fonts(args.font, args.bold_font)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    w0, h0, _ = page_geometry(1, trim_w, trim_h, args.bleed, gutter, args.outer, args.vmargin)
    # initialFontName matters: reportlab otherwise declares un-embedded Helvetica on every page,
    # and KDP requires all fonts to be embedded.
    c = canvas.Canvas(str(out), pagesize=(w0, h0), pageCompression=1, initialFontName=fonts[0])
    c.setTitle(args.title)
    c.setAuthor(args.author)
    c.setCreator("SideHustle build_interior.py")

    thresholds = []
    for idx, (kind, payload) in enumerate(plan, start=1):
        pw, ph, safe = page_geometry(idx, trim_w, trim_h, args.bleed, gutter, args.outer, args.vmargin)
        left, bottom, right, top = safe
        if kind == "art":
            g = load_gray(images[payload])
            if args.autocrop:
                g = autocrop(g)
            box_w_px = (right - left) / PT * DPI
            box_h_px = (top - bottom) / PT * DPI
            scale = min(box_w_px / g.width, box_h_px / g.height)
            g = g.resize((max(1, round(g.width * scale)), max(1, round(g.height * scale))), Image.LANCZOS)
            arr = np.asarray(g)
            thr = pick_threshold(arr, args.threshold)
            thresholds.append(thr)
            bw = Image.fromarray(np.where(arr >= thr, 255, 0).astype(np.uint8), "L")
            w_pt, h_pt = bw.width / DPI * PT, bw.height / DPI * PT
            x = left + ((right - left) - w_pt) / 2
            y = bottom + ((top - bottom) - h_pt) / 2
            c.drawImage(ImageReader(bw), x, y, width=w_pt, height=h_pt)
        elif kind in ("title", "copyright", "belongs"):
            draw_text_page(c, kind, args, fonts, pw, ph, safe)
        c.showPage()
    c.save()

    summary = validate_pdf(out, n_pages, w0 / PT, h0 / PT)
    summary.update(
        {
            "art_pages": len(images),
            "gutter_in": gutter,
            "bleed": args.bleed,
            "median_threshold": int(np.median(thresholds)) if thresholds else None,
        }
    )
    print(json.dumps(summary, indent=2))
    if summary["problems"]:
        print("\nProblems found, fix before uploading:", file=sys.stderr)
        for p in summary["problems"]:
            print(f"  - {p}", file=sys.stderr)
        return 1
    print(
        "\nNext: upload to KDP and check every page in KDP's online previewer before publishing."
    )
    return 0


def validate_pdf(path: Path, expect_pages: int, w_in: float, h_in: float) -> dict:
    problems: list[str] = []
    info: dict = {"file": str(path), "pages": expect_pages, "page_size_in": [round(w_in, 4), round(h_in, 4)]}
    size_mb = path.stat().st_size / 1e6
    info["size_mb"] = round(size_mb, 2)
    if size_mb > 650:
        problems.append("file exceeds KDP's 650 MB limit")
    try:
        from pypdf import PdfReader

        r = PdfReader(str(path))
        if len(r.pages) != expect_pages:
            problems.append(f"expected {expect_pages} pages, PDF has {len(r.pages)}")
        sizes = {(round(float(p.mediabox.width), 1), round(float(p.mediabox.height), 1)) for p in r.pages}
        if len(sizes) != 1:
            problems.append(f"pages are not a uniform size: {sorted(sizes)}")
        want = (round(w_in * PT, 1), round(h_in * PT, 1))
        if sizes and want not in sizes:
            problems.append(f"page size {sorted(sizes)} differs from expected {want}")
    except ImportError:
        info["validated_with"] = "reportlab only (install pypdf for page-size checks)"
    if shutil.which("pdffonts"):
        # pdffonts columns end with: emb sub uni object ID
        rows = subprocess.run(["pdffonts", str(path)], capture_output=True, text=True).stdout.splitlines()[2:]
        unembedded = []
        for ln in rows:
            m = re.search(r"\s(yes|no)\s+(?:yes|no)\s+(?:yes|no)\s+\d+\s+\d+\s*$", ln)
            if m and m.group(1) == "no":
                unembedded.append(ln.split()[0])
        if unembedded:
            problems.append(f"fonts not embedded: {unembedded}")
        info["fonts_embedded"] = not unembedded
    info["problems"] = problems
    return info


# ----------------------------------------------------------------------------- cover
def cmd_cover_dims(args) -> int:
    tw, th = args.trim
    spine = args.pages * SPINE_PER_PAGE[args.paper]
    total_w = 2 * tw + spine + 2 * BLEED_W
    total_h = th + BLEED_H
    px = lambda v: round(v * DPI)
    out = {
        "pages": args.pages,
        "paper": args.paper,
        "spine_in": round(spine, 4),
        "full_cover_in": [round(total_w, 4), round(total_h, 4)],
        "full_cover_px_300dpi": [px(total_w), px(total_h)],
        "front_panel_in": [tw, th],
        "bleed_in_each_side": BLEED_W,
        "spine_text_allowed": args.pages >= SPINE_TEXT_MIN_PAGES,
        "barcode_keepout": "leave a blank ~2.0 x 1.2 in area at the bottom-right of the back cover "
        "(KDP places the barcode there; VERIFY size)",
    }
    print(json.dumps(out, indent=2))
    print("\nVERIFY against KDP's cover calculator before making the final cover.")
    return 0


# ----------------------------------------------------------------------------- cli
def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    q = sub.add_parser("qa", help="check generated images")
    q.add_argument("images", type=Path)
    q.add_argument("--json", help="write full results to this file")
    q.add_argument("--strict", action="store_true", help="exit 1 if anything is flagged")
    q.set_defaults(func=cmd_qa)

    b = sub.add_parser("build", help="assemble the interior PDF")
    b.add_argument("images", type=Path)
    b.add_argument("-o", "--output", required=True)
    b.add_argument("--title", required=True)
    b.add_argument("--subtitle", default="")
    b.add_argument("--author", required=True, help="the pen name shown on the book")
    b.add_argument("--year", default="2026")
    b.add_argument("--note", default="", help="extra line on the copyright page")
    b.add_argument("--trim", type=parse_trim, default=(8.5, 11.0), help="trim size WxH inches (default 8.5x11)")
    b.add_argument("--bleed", action="store_true", help="make a full-bleed PDF (art stays inside margins)")
    b.add_argument("--outer", type=float, default=0.375, help="outer margin, inches (KDP min 0.25)")
    b.add_argument("--vmargin", type=float, default=0.375, help="top/bottom margin, inches")
    b.add_argument("--gutter", type=float, default=0, help="force a larger gutter than KDP's minimum")
    b.add_argument("--threshold", default="auto", help="'auto' or 0-255 black/white cutoff")
    b.add_argument("--no-autocrop", dest="autocrop", action="store_false")
    b.add_argument("--no-blank-backs", dest="blank_backs", action="store_false",
                   help="skip the blank page behind each image (not recommended: ink shows through)")
    b.add_argument("--no-belongs-to", dest="belongs_to", action="store_false")
    b.add_argument("--pad-to-min", action="store_true", help="pad with blank pages up to the KDP minimum")
    b.add_argument("--font", help="TrueType font for text pages (must be embeddable)")
    b.add_argument("--bold-font")
    b.set_defaults(func=cmd_build)

    cv = sub.add_parser("cover-dims", help="spine width and full-cover size")
    cv.add_argument("--pages", type=int, required=True)
    cv.add_argument("--trim", type=parse_trim, default=(8.5, 11.0))
    cv.add_argument("--paper", choices=sorted(SPINE_PER_PAGE), default="white")
    cv.set_defaults(func=cmd_cover_dims)
    return p


def main(argv=None) -> int:
    args = make_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
