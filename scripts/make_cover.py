#!/usr/bin/env python3
"""Compose a KDP paperback wrap-around cover (back + spine + front) for a coloring book.

Front art is an existing page image from the book (or any line-art image you supply). Title,
author and imprint text are drawn with PIL using an embeddable TrueType font; the result is
rasterized at 300 DPI and saved as a single-page PDF (what KDP asks for) plus a PNG preview.

Rules baked in (KDP help "Create a Paperback Cover", verified 2026-11-06):
  * cover width  = bleed + back + spine + front + bleed;  height = trim height + 2 x bleed
  * spine text only when the book has MORE than 79 pages; otherwise the spine stays blank
  * back cover keeps a blank white area for the barcode (KDP suggests 2 x 1.2 in, at least
    0.25 in from the spine and trim). If you leave it blank KDP places the barcode itself.

Usage:
  python3 scripts/make_cover.py books/NNN-slug/pages/01_*.png -o books/NNN-slug/cover.pdf \\
      --title "Cozy Winter Animals Coloring Book" --subtitle "30 Bold and Easy Pictures for Kids Ages 4-8" \\
      --author "Wren Ashby" --imprint "Little Fox Paper Co" --pages 64 --blurb "line one|line two"

Also writes <out>.png (flat preview) and <out>_guides.png (trim / bleed / spine / safe lines).
Always check the PDF in KDP's cover previewer before publishing.
"""
from __future__ import annotations

import argparse
import importlib.util
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

_SPEC = importlib.util.spec_from_file_location("build_interior", Path(__file__).resolve().parent / "build_interior.py")
bi = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(bi)

DPI = bi.DPI
SAFE = 0.4  # inches kept clear of the trim edge for text (KDP minimum is 0.25)
BARCODE_W, BARCODE_H = 2.0, 1.2  # KDP suggested barcode size, inches
BARCODE_MARGIN = 0.4  # from trim and from spine (KDP minimum 0.25)
SPINE_SAFE = 0.0625  # KDP: keep 1/16 in clear of the spine edges

BG = (206, 232, 245)  # pale winter blue
INK = (24, 52, 92)  # navy for text
PANEL = (255, 255, 255)
ACCENT = (232, 116, 90)  # warm coral for the banner


def px(inches: float) -> int:
    return round(inches * DPI)


def cover_geometry(pages: int, trim: tuple[float, float], paper: str = "white") -> dict:
    """All cover measurements in inches, using the constants from build_interior."""
    tw, th = trim
    spine = pages * bi.SPINE_PER_PAGE[paper]
    bw, bh = bi.BLEED_W, bi.BLEED_H / 2
    total_w = bw + tw + spine + tw + bw
    total_h = bh + th + bh
    return {
        "trim_w": tw, "trim_h": th, "spine": spine, "bleed_x": bw, "bleed_y": bh,
        "total_w": total_w, "total_h": total_h,
        "back_x0": bw, "back_x1": bw + tw,
        "spine_x0": bw + tw, "spine_x1": bw + tw + spine,
        "front_x0": bw + tw + spine, "front_x1": bw + tw + spine + tw,
        "top": bh, "bottom": bh + th,
        "spine_text": pages >= bi.SPINE_TEXT_MIN_PAGES,
    }


def barcode_box(g: dict) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) in inches of the blank barcode area: bottom-right of the back cover."""
    x1 = g["back_x1"] - BARCODE_MARGIN
    y1 = g["bottom"] - BARCODE_MARGIN
    return x1 - BARCODE_W, y1 - BARCODE_H, x1, y1


def find_font(user: str | None) -> str:
    if user:
        if not Path(user).is_file():
            sys.exit(f"font file not found: {user}")
        return user
    for c in bi.BOLD_CANDIDATES:
        if Path(c).is_file():
            return c
    sys.exit("no bold TrueType font found; pass --font /path/to/font.ttf")


def find_body_font(user: str | None, bold_path: str) -> str:
    if user:
        return user
    for c in bi.FONT_CANDIDATES:
        if Path(c).is_file():
            return c
    return bold_path


def fit_font(draw, text: str, path: str, max_w: int, start: int, min_size: int = 20) -> ImageFont.FreeTypeFont:
    size = start
    while size > min_size:
        f = ImageFont.truetype(path, size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return ImageFont.truetype(path, min_size)


def wrap(draw, text: str, font, max_w: int) -> list[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def centered(draw, cx: int, y: int, text: str, font, fill) -> int:
    w = draw.textlength(text, font=font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)
    a, d = font.getmetrics()
    return y + a + d


def line_art_panel(art_path: Path, size: tuple[int, int]) -> Image.Image:
    """White rounded panel containing the line art, fitted inside `size`."""
    pw, ph = size
    panel = Image.new("RGB", size, PANEL)
    art = Image.open(art_path).convert("L")
    art = ImageOps.autocontrast(art)
    box = art.point(lambda v: 255 if v < 200 else 0).getbbox()  # crop to the ink, keep a small pad
    if box:
        pad = int(0.03 * max(art.size))
        art = art.crop((max(0, box[0] - pad), max(0, box[1] - pad), min(art.width, box[2] + pad), min(art.height, box[3] + pad)))
    inner = (int(pw * 0.92), int(ph * 0.92))
    scale = min(inner[0] / art.width, inner[1] / art.height)
    art = art.resize((max(1, round(art.width * scale)), max(1, round(art.height * scale))), Image.LANCZOS)
    panel.paste(art.convert("RGB"), ((pw - art.width) // 2, (ph - art.height) // 2))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=px(0.3), fill=255)
    out = Image.new("RGBA", size, (0, 0, 0, 0))
    out.paste(panel, (0, 0), mask)
    return out


def snow_dots(img: Image.Image, g: dict, seed: int = 7) -> None:
    """A few white dots on the background only (kept away from text zones by being faint and sparse)."""
    rnd = random.Random(seed)
    d = ImageDraw.Draw(img)
    W, H = img.size
    for _ in range(70):
        x, y = rnd.randrange(W), rnd.randrange(H)
        r = rnd.choice([6, 9, 12, 16])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 246, 252))


def title_lines(title: str) -> list[str]:
    """Split a title into short display lines; a trailing 'Coloring Book' gets its own line."""
    words = title.split()
    tail = []
    if len(words) > 2 and " ".join(words[-2:]).lower() == "coloring book":
        words, tail = words[:-2], [" ".join(title.split()[-2:])]
    n = 2 if len(words) >= 3 else len(words)
    per = -(-len(words) // max(n, 1)) if words else 1
    return [" ".join(words[i:i + per]) for i in range(0, len(words), per)] + tail


def draw_front(img, g, a, title_font_path, body_font_path, art_path) -> None:
    d = ImageDraw.Draw(img)
    x0, x1 = px(g["front_x0"]), px(g["front_x1"])
    top, bottom = px(g["top"]), px(g["bottom"])
    cx = (x0 + x1) // 2
    safe_w = (x1 - x0) - 2 * px(SAFE)

    lines = title_lines(a.title)
    y = top + px(SAFE)
    size = px(0.8)
    fonts = [fit_font(d, ln, title_font_path, safe_w, size) for ln in lines]
    f = min(fonts, key=lambda ft: ft.size)  # one size for all lines
    for ln in lines:
        y = centered(d, cx, y, ln, f, INK)

    # art panel
    art_top = y + px(0.15)
    sub_h = px(0.9) if a.subtitle else 0
    author_h = px(1.25)
    art_bottom = bottom - px(SAFE) - author_h - sub_h
    ph = art_bottom - art_top
    pw = min(safe_w, int(ph * 0.95))
    ph = min(ph, int(pw * 1.2))
    panel = line_art_panel(art_path, (pw, ph))
    img.paste(panel, (cx - pw // 2, art_top), panel)

    # subtitle banner
    yy = art_top + ph + px(0.15)
    if a.subtitle:
        sf = fit_font(d, a.subtitle, body_font_path, safe_w - px(0.4), px(0.3))
        tw = d.textlength(a.subtitle, font=sf)
        asc, desc = sf.getmetrics()
        bh = asc + desc + px(0.16)
        d.rounded_rectangle([cx - tw / 2 - px(0.2), yy, cx + tw / 2 + px(0.2), yy + bh], radius=px(0.12), fill=ACCENT)
        d.text((cx - tw / 2, yy + px(0.08)), a.subtitle, font=sf, fill=(255, 255, 255))
        yy += bh + px(0.12)

    # author + imprint at the bottom of the safe area
    af = fit_font(d, a.author, title_font_path, safe_w, px(0.5))
    ay = bottom - px(SAFE) - px(0.95)
    ay = max(ay, yy)
    ay = centered(d, cx, ay, a.author, af, INK)
    if a.imprint:
        imf = ImageFont.truetype(body_font_path, px(0.19))
        centered(d, cx, ay + px(0.04), a.imprint, imf, INK)


def draw_back(img, g, a, title_font_path, body_font_path) -> None:
    d = ImageDraw.Draw(img)
    x0, x1 = px(g["back_x0"]), px(g["back_x1"])
    top = px(g["top"])
    cx = (x0 + x1) // 2
    safe_w = (x1 - x0) - 2 * px(SAFE + 0.2)
    y = top + px(SAFE + 0.5)
    hf = fit_font(d, a.title, title_font_path, safe_w, px(0.42))
    for ln in wrap(d, a.title, hf, safe_w):
        y = centered(d, cx, y, ln, hf, INK)
    y += px(0.3)
    bf = ImageFont.truetype(body_font_path, px(0.26))
    for para in a.blurb:
        for ln in wrap(d, para, bf, safe_w):
            y = centered(d, cx, y, ln, bf, INK) + px(0.04)
        y += px(0.22)
    # barcode keep-out: solid white, nothing inside
    bx0, by0, bx1, by1 = (px(v) for v in barcode_box(g))
    d.rectangle([bx0, by0, bx1, by1], fill=(255, 255, 255))
    if a.imprint:
        imf = ImageFont.truetype(body_font_path, px(0.19))
        centered(d, cx, by0 - px(0.5), a.imprint, imf, INK)


def draw_spine(img, g, a, title_font_path, body_font_path) -> None:
    if not g["spine_text"]:
        return
    x0, x1 = px(g["spine_x0"]), px(g["spine_x1"])
    top, bottom = px(g["top"]), px(g["bottom"])
    sw, sh = x1 - x0 - 2 * px(SPINE_SAFE), bottom - top - 2 * px(SAFE)
    if sw <= 0:
        return
    strip = Image.new("RGBA", (sh, sw), (0, 0, 0, 0))
    d = ImageDraw.Draw(strip)
    text = f"{a.title}   |   {a.author}"
    f = fit_font(d, text, title_font_path, sh, px(0.5))
    asc, desc = f.getmetrics()
    d.text(((sh - d.textlength(text, font=f)) / 2, (sw - (asc + desc)) / 2), text, font=f, fill=INK + (255,))
    rot = strip.rotate(-90, expand=True)  # reads top-to-bottom, as US paperbacks do
    img.paste(rot, (x0 + px(SPINE_SAFE), top + px(SAFE)), rot)


def draw_guides(img: Image.Image, g: dict) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    red, blue, green = (230, 30, 30), (30, 90, 230), (20, 160, 60)
    bx0, bx1, by0, by1 = px(g["bleed_x"]), px(g["total_w"] - g["bleed_x"]), px(g["bleed_y"]), px(g["total_h"] - g["bleed_y"])
    d.rectangle([bx0, by0, bx1, by1], outline=red, width=4)  # trim
    for x in (g["spine_x0"], g["spine_x1"]):
        d.line([px(x), 0, px(x), out.height], fill=blue, width=4)
    for x0, x1 in ((g["back_x0"], g["back_x1"]), (g["front_x0"], g["front_x1"])):
        d.rectangle([px(x0 + SAFE), px(g["top"] + SAFE), px(x1 - SAFE), px(g["bottom"] - SAFE)], outline=green, width=3)
    bb = barcode_box(g)
    d.rectangle([px(bb[0]), px(bb[1]), px(bb[2]), px(bb[3])], outline=(160, 0, 160), width=4)
    return out


def compose(a, g: dict) -> Image.Image:
    img = Image.new("RGB", (px(g["total_w"]), px(g["total_h"])), BG)
    snow_dots(img, g)
    title_font = find_font(a.bold_font)
    body_font = find_body_font(a.font, title_font)
    draw_front(img, g, a, title_font, body_font, Path(a.art))
    draw_back(img, g, a, title_font, body_font)
    draw_spine(img, g, a, title_font, body_font)
    return img


def save_pdf(img: Image.Image, path: Path, g: dict) -> None:
    w_pt, h_pt = g["total_w"] * 72.0, g["total_h"] * 72.0
    c = canvas.Canvas(str(path), pagesize=(w_pt, h_pt), pageCompression=1)
    c.drawImage(ImageReader(img), 0, 0, width=w_pt, height=h_pt)
    c.showPage()
    c.save()


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("art", help="line-art image for the front (usually one of the book's pages)")
    p.add_argument("-o", "--output", required=True, help="cover PDF path; PNG previews are written beside it")
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", default="")
    p.add_argument("--author", required=True, help="pen name")
    p.add_argument("--imprint", default="")
    p.add_argument("--pages", type=int, required=True, help="final interior page count")
    p.add_argument("--trim", type=bi.parse_trim, default=(8.5, 11.0))
    p.add_argument("--paper", choices=sorted(bi.SPINE_PER_PAGE), default="white")
    p.add_argument("--blurb", default="", help="back-cover lines separated by '|'")
    p.add_argument("--font", help="body TrueType font")
    p.add_argument("--bold-font", help="bold TrueType font")
    return p


def main(argv=None) -> int:
    a = make_parser().parse_args(argv)
    a.blurb = [s.strip() for s in a.blurb.split("|") if s.strip()]
    if not Path(a.art).is_file():
        print(f"art file not found: {a.art}", file=sys.stderr)
        return 2
    if not bi.MIN_PAGES <= a.pages <= bi.MAX_PAGES:
        print(f"--pages must be {bi.MIN_PAGES}-{bi.MAX_PAGES}", file=sys.stderr)
        return 2
    g = cover_geometry(a.pages, a.trim, a.paper)
    img = compose(a, g)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    save_pdf(img, out, g)
    img.save(out.with_suffix(".png"), dpi=(DPI, DPI))
    draw_guides(img, g).save(out.with_name(out.stem + "_guides.png"), dpi=(DPI, DPI))
    print(
        f"cover: {g['total_w']:.4f} x {g['total_h']:.4f} in ({img.width} x {img.height} px), "
        f"spine {g['spine']:.4f} in, spine text: {'yes' if g['spine_text'] else 'no (under the KDP page minimum)'}"
    )
    print(f"wrote {out}, {out.with_suffix('.png')}, {out.with_name(out.stem + '_guides.png')}")
    print("Check the PDF in KDP's cover previewer / cover calculator before publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
