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

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
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


CRAYONS = [
    (231, 76, 60), (243, 156, 18), (247, 202, 24), (46, 184, 114), (26, 188, 156), (52, 152, 219),
    (155, 89, 182), (236, 112, 167), (140, 198, 63), (255, 138, 101), (100, 181, 246), (186, 104, 200),
]


def _boundary_x(h: int, w: int, split: float, tilt: float, rng, jitter: bool) -> np.ndarray:
    """x position (px) of the edge of the colored area for every row: a tilted line with a
    back-and-forth zigzag (like scribbled strokes) plus a little wobble."""
    y = np.arange(h, dtype=np.float32)
    bx = w * (split + tilt * (y / h - 0.5))
    if jitter:
        stroke = max(10.0, h / 90)
        zig = (((y / stroke) % 2.0) - 1.0)  # triangle wave in [-1, 1]
        bx = bx + np.abs(zig) * (w * 0.022) - w * 0.011
        wob = np.convolve(rng.normal(0, 1, h), np.ones(25) / 25, mode="same")
        bx = bx + wob * w * 0.03
    return bx


def colorize_half(gray: Image.Image, seed: int = 3, split: float = 0.5, tilt: float = 0.3,
                  jitter: bool = True, min_area_frac: float = 0.0012):
    """Fill the enclosed regions of black-line art with crayon colors on one side of a scribbled
    edge (left/bottom), leaving the rest as plain line art. Returns (RGB image, (tip_x, tip_y) as
    fractions of the image where a crayon should rest, the crayon's RGB color = the fill it is touching). Lines are untouched (colors are multiplied
    under them), the outside background stays white, and tiny regions (eye highlights) stay white."""
    from scipy import ndimage

    rng = np.random.default_rng(seed)
    arr = np.asarray(gray.convert("L"), dtype=np.float32)
    h, w = arr.shape
    ink = arr < 160
    regions, n = ndimage.label(~ink)
    if n == 0:
        return gray.convert("RGB"), (0.5, 0.8), ACCENT
    border = np.unique(np.concatenate([regions[0], regions[-1], regions[:, 0], regions[:, -1]]))
    sizes = np.bincount(regions.ravel(), minlength=n + 1)
    # every pixel (including line pixels) takes the label of its nearest region, so colors sit under the lines
    idx = ndimage.distance_transform_edt(regions == 0, return_distances=False, return_indices=True)
    full = regions[idx[0], idx[1]]
    colorable = [lab for lab in range(1, n + 1) if lab not in border and sizes[lab] >= min_area_frac * h * w]
    # neighbours (regions touching across a line) must not share a color
    nb: dict[int, set] = {lab: set() for lab in colorable}
    for a, b in ((full[:, :-1], full[:, 1:]), (full[:-1, :], full[1:, :])):
        diff = a != b
        for u, v in set(zip(a[diff].tolist(), b[diff].tolist())):
            if u in nb and v in nb:
                nb[u].add(v)
                nb[v].add(u)
    chosen: dict[int, tuple] = {}
    for lab in sorted(colorable, key=lambda L: -sizes[L]):
        used = {chosen[o] for o in nb[lab] if o in chosen}
        free = [c for c in CRAYONS if c not in used] or CRAYONS
        chosen[lab] = free[int(rng.integers(len(free)))]
    lut = np.full((n + 1, 3), 255.0, dtype=np.float32)
    for lab, c in chosen.items():
        lut[lab] = c
    color = lut[full]

    # crayon-on-paper texture: grain plus diagonal hatching, blended toward white
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    grain = ndimage.gaussian_filter(rng.normal(0, 1, (h, w)).astype(np.float32), 1.0)
    grain /= max(float(np.abs(grain).max()), 1e-6)
    period = max(6.0, w / 140)
    hatch = 0.5 + 0.5 * np.sin((xx + yy) / period * 2 * np.pi + grain * 2.0)
    amount = np.clip(0.80 + 0.12 * grain - 0.10 * hatch, 0.55, 0.95)[..., None]
    color = 255.0 * (1 - amount) + color * amount

    bx = _boundary_x(h, w, split, tilt, rng, jitter)
    colored = xx < bx[:, None]
    layer = np.where(colored[..., None], color, 255.0)
    out = np.clip(layer * (arr[..., None] / 255.0), 0, 255).astype(np.uint8)
    ty = 0.74
    row = int(ty * h)
    tx = float(bx[row]) / w
    col = int(max(0, min(w - 1, bx[row] - 0.02 * w)))
    crayon = tuple(int(v) for v in lut[full[row, col]])
    if crayon == (255, 255, 255):
        crayon = ACCENT
    return Image.fromarray(out, "RGB"), (min(max(tx, 0.05), 0.95), ty), crayon


def draw_crayon(panel: Image.Image, tip: tuple[float, float], color=ACCENT, scale: int = 3) -> None:
    """Draw a crayon resting on the paper with its point at `tip` (pixels); body trails right/down."""
    import math

    ang = math.radians(28)
    length, width = panel.width * 0.46, panel.width * 0.065
    tx, ty = tip
    S = scale
    ov = Image.new("RGBA", (panel.width * S, panel.height * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    ux, uy = math.cos(ang), math.sin(ang)  # along the body, away from the tip
    nx, ny = -uy, ux
    tip_len = width * 1.4

    def pt(along, across):
        return ((tx + ux * along + nx * across) * S, (ty + uy * along + ny * across) * S)

    dark = tuple(int(c * 0.65) for c in color)
    d.polygon([pt(0, 0), pt(tip_len, -width / 2), pt(tip_len, width / 2)], fill=color, outline=dark)  # point
    d.polygon([pt(tip_len, -width / 2), pt(length, -width / 2), pt(length, width / 2), pt(tip_len, width / 2)],
              fill=color, outline=dark)  # body
    wrap0, wrap1 = tip_len + width * 1.2, length - width * 0.8
    d.polygon([pt(wrap0, -width / 2), pt(wrap1, -width / 2), pt(wrap1, width / 2), pt(wrap0, width / 2)],
              fill=(250, 244, 230), outline=dark)  # paper wrapper
    for k in (0.3, 0.7):  # two thin stripes on the wrapper
        a = wrap0 + (wrap1 - wrap0) * k
        d.line([pt(a, -width / 2), pt(a, width / 2)], fill=dark, width=max(2, S))
    ov = ov.resize(panel.size, Image.LANCZOS)
    panel.alpha_composite(ov) if panel.mode == "RGBA" else panel.paste(ov, (0, 0), ov)


def line_art_panel(art_path: Path, size: tuple[int, int], colorize: bool = False, seed: int = 3) -> Image.Image:
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
    tip, crayon = None, ACCENT
    rgb = art.convert("RGB")
    if colorize:
        rgb, tip, crayon = colorize_half(art, seed=seed)
    art_w, art_h = max(1, round(art.width * scale)), max(1, round(art.height * scale))
    rgb = rgb.resize((art_w, art_h), Image.LANCZOS)
    ox, oy = (pw - art_w) // 2, (ph - art_h) // 2
    panel.paste(rgb, (ox, oy))
    if colorize and tip:
        draw_crayon(panel, (ox + tip[0] * art_w, oy + tip[1] * art_h), color=crayon)
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


def draw_front(img, g, a, title_font_path, body_font_path, art_path) -> None:  # noqa: C901
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
    panel = line_art_panel(art_path, (pw, ph), colorize=a.colored_half, seed=a.seed)
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
    p.add_argument("--colored-half", action="store_true",
                   help="color in half of the front art (crayon look, with a crayon) and leave the rest line art")
    p.add_argument("--seed", type=int, default=3, help="random seed for the crayon colors")
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
