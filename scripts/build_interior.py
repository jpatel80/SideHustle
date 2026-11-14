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
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

DPI = 300  # KDP minimum for images; covers are rendered at this resolution
ART_DPI = 600  # interior line art is rendered at 600 DPI so thresholded edges stay smooth in print
PT = 72.0
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

# Verified 2026-11-06 against KDP help "Set Trim Size, Bleed, and Margins" (GVBQ3CMEQW3W2VL6): minimum inside (gutter) margin by page count.
GUTTER_TABLE = [(150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875)]
MIN_PAGES = 24  # Verified 2026-11-06 (KDP Paperback Submission Guidelines): smallest paperback page count.
MAX_PAGES = 828  # Largest page count in the gutter table (the limit for small trims).
MAX_PAGES_LARGE_TRIM = 590  # 8.5 x 11 in, black ink, white paper: 24-590 pages (KDP, 2026-11-06).
DEFAULT_GUTTER = 0.5  # we use more than KDP's 0.375 in minimum so art near the binding is easier to color
BLEED_W = 0.125  # extra width for a full-bleed PDF (outer edge only)
BLEED_H = 0.25  # extra height for a full-bleed PDF (top + bottom)
# Verified 2026-11-06 (KDP "Create a Paperback Cover", G201953020): spine thickness per page, inches.
SPINE_PER_PAGE = {"white": 0.002252, "cream": 0.0025, "premium-color": 0.002347}
SPINE_TEXT_MIN_PAGES = 80  # KDP: spine text only on books with MORE than 79 pages (Cover Creator says 80). Verified 2026-11-06.

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
MAX_GRAY_RATIO = 0.01  # share of pixels inside FLAT gray areas (anti-aliased line edges are not counted)
GRAY_FLAT_PX = 5  # a pixel is "flat gray" when its whole 5x5 neighbourhood is mid-gray
MAX_INK_RATIO = 0.30
MIN_INK_RATIO = 0.01
MIN_SIDE_PX = 1000  # openai/gpt-image-2 returns 1152 x 1536 px at 3:4; below ~1000 px lines get soft
SPECK_IN = 0.045  # an enclosed white area smaller than this (inches across, at print size) cannot be colored
MAX_SPECKS = {"kids": 25, "adult": 400}  # tiny enclosed areas allowed per page before it is flagged as "crackly"
LINE_WEIGHT_SPREAD = 1.6  # flag pages whose line weight is this many times above/below the book median
DUP_HAMMING = 16  # of 256 hash bits


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


def max_pages_for(trim: tuple[float, float]) -> int:
    """KDP page limit for black ink on white paper (large trims stop at 590 pages)."""
    w, h = trim
    return MAX_PAGES_LARGE_TRIM if (w > 6.12 or h > 9.0) else MAX_PAGES


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
    # 16 x 16 difference hash (256 bits): the old 8 x 8 hash called different sparse line drawings duplicates
    small = np.asarray(gray.resize((17, 16), Image.LANCZOS), dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


# ----------------------------------------------------------------------------- qa
def _probe(gray: Image.Image) -> Image.Image:
    w, h = gray.size
    if max(w, h) > 1536:  # speed: statistics are scale-stable enough
        s = 1536 / max(w, h)
        return gray.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    return gray


def analyse_image(path: Path, style: str = "kids") -> dict:
    gray = load_gray(path)
    w, h = gray.size
    probe = _probe(gray)
    a = np.asarray(probe)
    # flat gray = shading or a gray fill. Anti-aliased edges of thin lines are mid-gray too, but never
    # fill a whole neighbourhood, so they no longer trip this check on finely detailed (adult) pages.
    mid = Image.fromarray((((a > GRAY_LO) & (a < GRAY_HI)) * 255).astype(np.uint8), "L")
    gray_ratio = float((np.asarray(mid.filter(ImageFilter.MinFilter(GRAY_FLAT_PX))) > 0).mean())
    ink_ratio = float((a < 128).mean())
    ink = a < 128
    line_px, specks = line_stats(ink, probe.width)
    border = 3  # ink in the outermost pixels means the picture was cut off by the image edge
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
    if touches and style == "kids":  # adult pages are full-page compositions; reaching the edge is normal there
        flags.append("artwork is cut off at the image edge")
    if specks is not None and specks > MAX_SPECKS[style]:
        flags.append(f"crackly detail ({specks} enclosed areas too small to color; limit {MAX_SPECKS[style]})")
    return {
        "file": path.name,
        "size_px": [w, h],
        "gray_ratio": round(gray_ratio, 4),
        "ink_ratio": round(ink_ratio, 4),
        "line_px": line_px,
        "specks": specks,
        "touches_edge": touches,
        "flags": flags,
        "_hash": dhash(probe),
    }


def line_stats(ink: np.ndarray, width_px: int, page_width_in: float = 7.5) -> tuple[float | None, int | None]:
    """(typical line thickness in probe pixels, number of enclosed white areas too small to color).

    Line thickness is twice the mean distance-to-paper along the ridge of the ink (its local maxima).
    A "speck" is an enclosed white region smaller than SPECK_IN across when the image is printed
    `page_width_in` wide: lots of them means texture that turned into noise. Needs scipy; returns
    (None, None) without it."""
    try:
        from scipy import ndimage
    except ImportError:
        return None, None
    if not ink.any():
        return 0.0, 0
    dist = ndimage.distance_transform_edt(ink)
    ridge = ink & (dist >= ndimage.maximum_filter(dist, size=3) - 1e-6)
    line_px = round(float(2 * dist[ridge].mean() - 1), 2) if ridge.any() else 0.0
    regions, n = ndimage.label(~ink)
    if n == 0:
        return line_px, 0
    sizes = np.bincount(regions.ravel(), minlength=n + 1)[1:]
    speck_area = (SPECK_IN * width_px / page_width_in) ** 2
    return line_px, int((sizes < speck_area).sum())


def run_qa(images: list[Path], style: str = "kids", against: list[Path] | None = None) -> list[dict]:
    results = [analyse_image(p, style) for p in images]
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            if hamming(results[i]["_hash"], results[j]["_hash"]) <= DUP_HAMMING:
                for k, other in ((i, j), (j, i)):
                    results[k]["flags"].append(f"near-duplicate of {results[other]['file']}")
    for other_path in against or []:  # pages of other books in the catalog: no picture may repeat
        try:
            oh = dhash(_probe(load_gray(other_path)))
        except OSError:
            continue
        for r in results:
            if hamming(r["_hash"], oh) <= DUP_HAMMING:
                r["flags"].append(f"near-duplicate of another book's page: {other_path.parent.parent.parent.name}/{other_path.name}")
    weights = [r["line_px"] for r in results if r["line_px"]]
    if len(weights) >= 5:
        med = float(np.median(weights))
        for r in results:
            if r["line_px"] and (r["line_px"] > med * LINE_WEIGHT_SPREAD or r["line_px"] < med / LINE_WEIGHT_SPREAD):
                r["flags"].append(f"line weight {r['line_px']:.1f}px differs from the book's median {med:.1f}px")
    for r in results:
        r.pop("_hash")
    return results


def cmd_qa(args) -> int:
    images = list_images(args.images)
    if not images:
        print(f"No images found in {args.images}", file=sys.stderr)
        return 2
    against = []
    for folder in args.against or []:
        against += list_images(Path(folder))
    results = run_qa(images, args.style, against)
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


def register_fonts(font: str | None, bold: str | None, display: str | None = "auto") -> tuple[str, str, str]:
    reg = find_font(font, FONT_CANDIDATES, "font")
    if not reg:
        sys.exit(
            "No TrueType font found. KDP requires embedded fonts, so pass --font /path/to/font.ttf "
            "(any font you have the licence to embed)."
        )
    bld = find_font(bold, BOLD_CANDIDATES, "bold font") or reg
    pdfmetrics.registerFont(TTFont("BodyFont", reg))
    pdfmetrics.registerFont(TTFont("BoldFont", bld))
    # display font for headings on the title / name / test pages: Chewy (kids) unless told otherwise
    if display == "auto":
        display = str(DISPLAY_FONT) if DISPLAY_FONT.is_file() else None
    if display in (None, "", "none"):
        return "BodyFont", "BoldFont", "BoldFont"
    if not Path(display).is_file():
        sys.exit(f"--display-font file not found: {display}")
    pdfmetrics.registerFont(TTFont("DisplayFont", display))
    return "BodyFont", "BoldFont", "DisplayFont"


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


DISPLAY_FONT = Path(__file__).resolve().parent.parent / "assets" / "fonts" / "Chewy-Regular.ttf"  # Apache 2.0
AI_NOTE = "The illustrations in this book were generated with AI image tools and were selected and arranged by the publisher."


def copyright_lines(a) -> list[str]:
    """Copyright page text. AI-generated pictures may not be protected by copyright, so the notice
    claims only what a person did (selection, arrangement, design) and states the AI use plainly."""
    owner = a.imprint or a.author
    lines = [
        a.title + (f": {a.subtitle}" if a.subtitle else ""),
        f"Selection, arrangement and design \u00a9 {a.year} {owner}.",
    ]
    if a.ai_note:
        lines.append(AI_NOTE)
    lines.append(
        "You are welcome to copy the pages for your own personal coloring. Please do not resell or "
        "redistribute this book or its pages."
    )
    if a.imprint:
        lines.append(f"Published by {a.imprint}")
    if a.note:
        lines.append(a.note)
    return lines


def threshold_art(gray: Image.Image, box_w_pt: float, box_h_pt: float, setting: str, dpi: int, crop: bool = True):
    """Fit a grayscale page into a box (points) at `dpi` and convert it to pure black and white.
    Returns (image, threshold used)."""
    if crop:
        gray = autocrop(gray)
    scale = min(box_w_pt / PT * dpi / gray.width, box_h_pt / PT * dpi / gray.height)
    g = gray.resize((max(1, round(gray.width * scale)), max(1, round(gray.height * scale))), Image.LANCZOS)
    arr = np.asarray(g)
    thr = pick_threshold(arr, setting)
    return Image.fromarray(np.where(arr >= thr, 255, 0).astype(np.uint8), "L"), thr


def place_image(c, bw: Image.Image, dpi: int, left: float, bottom: float, right: float, top: float) -> None:
    w_pt, h_pt = bw.width / dpi * PT, bw.height / dpi * PT
    c.drawImage(ImageReader(bw), left + ((right - left) - w_pt) / 2, bottom + ((top - bottom) - h_pt) / 2,
                width=w_pt, height=h_pt)


def split_title(title: str) -> list[str]:
    m = re.search(r"\bcoloring book\b", title, flags=re.I)
    if not m or (m.start() == 0 and m.end() == len(title)):
        return [title]
    return [t for t in (title[:m.start()].strip(), title[m.start():m.end()], title[m.end():].strip()) if t]


def draw_text_page(c, kind, a, fonts, page_w, page_h, safe, title_art: Image.Image | None = None):
    body, bold = fonts[0], fonts[1]
    display = fonts[2] if len(fonts) > 2 else bold
    left, bottom, right, top = safe
    cx_w = right - left
    c.setFillGray(0)
    c.setStrokeGray(0)
    if kind == "title":
        y = top - 70
        for part in split_title(a.title):  # "Coloring Book" stays together on its own line
            y = draw_centered_text(c, part, display, 46, y, page_w, cx_w)
        if a.subtitle:
            y = draw_centered_text(c, a.subtitle, body, 19, y - 6, page_w, cx_w)
        foot = bottom + 95
        if title_art is not None:  # one picture from the book, so the first page is not bare
            box = (left + cx_w * 0.14, foot + 28, right - cx_w * 0.14, y - 6)
            bw, _ = threshold_art(title_art, box[2] - box[0], box[3] - box[1], a.threshold, a.dpi)
            place_image(c, bw, a.dpi, *box)
        draw_centered_text(c, f"by {a.author}", body, 18, foot - 10, page_w, cx_w)
        if a.imprint:
            draw_centered_text(c, a.imprint, body, 13, foot - 40, page_w, cx_w)
    elif kind == "copyright":
        y = bottom + 190  # bottom of the page, where copyright notices usually sit
        for t in copyright_lines(a):
            y = draw_centered_text(c, t, body, 10, y, page_w, cx_w * 0.86) - 8
    elif kind == "belongs":
        c.setLineWidth(3)
        c.roundRect(left + 18, bottom + 18, cx_w - 36, (top - bottom) - 36, 28)
        c.setLineWidth(1.2)
        c.roundRect(left + 30, bottom + 30, cx_w - 60, (top - bottom) - 60, 20)
        draw_centered_text(c, "This book belongs to", display, 40, page_h * 0.62, page_w, cx_w - 90)
        c.setLineWidth(2)
        c.line(left + cx_w * 0.18, page_h * 0.47, right - cx_w * 0.18, page_h * 0.47)
    elif kind == "test":
        y = draw_centered_text(c, "Color test page", display, 36, top - 60, page_w, cx_w)
        y = draw_centered_text(c, "Try your crayons, pencils and markers here first.", body, 14, y - 4, page_w, cx_w)
        cols, rows = 4, 5
        gap = 16.0
        cell = min((cx_w - (cols - 1) * gap) / cols, (y - 30 - bottom - (rows - 1) * gap) / rows)
        x0 = left + (cx_w - (cols * cell + (cols - 1) * gap)) / 2
        c.setLineWidth(2.5)
        for r in range(rows):
            for k in range(cols):
                x, yy = x0 + k * (cell + gap), y - 30 - (r + 1) * cell - r * gap
                if (r + k) % 2:
                    c.circle(x + cell / 2, yy + cell / 2, cell / 2)
                else:
                    c.roundRect(x, yy, cell, cell, cell * 0.18)


def build_plan(n_art: int, a) -> list[tuple[str, int | None]]:
    plan: list[tuple[str, int | None]] = [("title", None), ("copyright", None)]
    if a.belongs_to:
        plan += [("belongs", None), ("blank", None)]
    for i in range(n_art):
        plan.append(("art", i))
        if a.blank_backs:
            plan.append(("blank", None))
    if a.test_page:  # last leaf, so marker tests cannot bleed onto a picture
        if len(plan) % 2:
            plan.append(("blank", None))
        plan += [("test", None), ("blank", None)]
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
            at = len(plan) - 2 if args.test_page else len(plan)  # keep the test page on the last leaf
            while len(plan) < MIN_PAGES:
                plan.insert(at, ("blank", None))
        else:
            need = MIN_PAGES - len(plan)
            per_image = 2 if args.blank_backs else 1
            print(
                f"Only {len(plan)} pages; KDP needs at least {MIN_PAGES}. Add ~{-(-need // per_image)} more "
                "images, or pass --pad-to-min to pad with blank pages.",
                file=sys.stderr,
            )
            return 2
    limit = max_pages_for(args.trim)
    if len(plan) > limit:
        print(f"{len(plan)} pages exceeds KDP's {limit}-page limit for this trim size.", file=sys.stderr)
        return 2

    n_pages = len(plan)
    gutter = max(gutter_for(n_pages), args.gutter or 0)
    fonts = register_fonts(args.font, args.bold_font, args.display_font)
    dpi = args.dpi
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
            bw, thr = threshold_art(load_gray(images[payload]), right - left, top - bottom, args.threshold, dpi,
                                    crop=args.autocrop)
            thresholds.append(thr)
            place_image(c, bw, dpi, left, bottom, right, top)
        elif kind in ("title", "copyright", "belongs", "test"):
            title_art = None
            if kind == "title" and args.title_art:
                src = images[min(max(args.title_art, 1), len(images)) - 1]
                title_art = load_gray(src)  # fitted to the space left on the title page when it is drawn
            draw_text_page(c, kind, args, fonts, pw, ph, safe, title_art)
        c.showPage()
    c.save()

    summary = validate_pdf(out, n_pages, w0 / PT, h0 / PT)
    summary.update(
        {
            "art_pages": len(images),
            "gutter_in": gutter,
            "art_dpi": dpi,
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
        "(KDP suggests 2 x 1.2 in, min 1.4 x 0.8, at least 0.25 in from spine and trim; verified 2026-11-06; if you leave it blank KDP adds the barcode itself)",
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
    q.add_argument("--style", choices=sorted(MAX_SPECKS), default="kids",
                   help="kids: bold simple pages; adult: fine detail is expected (higher tiny-area limit)")
    q.add_argument("--against", nargs="*", metavar="DIR", help="page folders of other books, to catch repeated pictures")
    q.set_defaults(func=cmd_qa)

    b = sub.add_parser("build", help="assemble the interior PDF")
    b.add_argument("images", type=Path)
    b.add_argument("-o", "--output", required=True)
    b.add_argument("--title", required=True)
    b.add_argument("--subtitle", default="")
    b.add_argument("--author", required=True, help="the pen name shown on the book")
    b.add_argument("--year", default=str(datetime.date.today().year))
    b.add_argument("--note", default="", help="extra line on the copyright page")
    b.add_argument("--no-ai-note", dest="ai_note", action="store_false",
                   help="omit the 'generated with AI image tools' line (only for books with no AI-generated art)")
    b.add_argument("--no-test-page", dest="test_page", action="store_false",
                   help="skip the color test page on the last leaf")
    b.add_argument("--title-art", type=int, default=1, metavar="N",
                   help="picture number shown small on the title page (0 = none, default 1)")
    b.add_argument("--display-font", default="auto",
                   help="TrueType font for headings; 'auto' = Chewy from assets/fonts, 'none' = the bold font")
    b.add_argument("--dpi", type=int, default=ART_DPI, help=f"resolution of the line art in the PDF (default {ART_DPI})")
    b.add_argument("--imprint", default="", help="imprint / brand line on the title and copyright pages")
    b.add_argument("--trim", type=parse_trim, default=(8.5, 11.0), help="trim size WxH inches (default 8.5x11)")
    b.add_argument("--bleed", action="store_true", help="make a full-bleed PDF (art stays inside margins)")
    b.add_argument("--outer", type=float, default=0.375, help="outer margin, inches (KDP min 0.25)")
    b.add_argument("--vmargin", type=float, default=0.375, help="top/bottom margin, inches")
    b.add_argument("--gutter", type=float, default=DEFAULT_GUTTER,
                   help=f"inside margin, inches (default {DEFAULT_GUTTER}; never below KDP's minimum for the page count)")
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
