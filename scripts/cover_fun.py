"""Playful decoration helpers for scripts/make_cover.py (the "fun" cover style).

Everything is drawn with PIL: a vertical gradient, a faint sunburst, snowflakes, confetti,
bouncy rainbow-letter titles with a white sticker halo, a starburst badge, a ribbon banner and
framed, tilted panels. Colors are all bright (no near-black outside text and outlines), and every
scatter helper takes `avoid` rectangles so the spine and the barcode area stay clean.
"""
from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

NAVY = (24, 52, 92)
WHITE = (255, 255, 255)
CORAL = (232, 92, 92)
SUN = (255, 205, 60)
FUN_COLORS = [
    (231, 76, 60), (243, 156, 18), (247, 202, 24), (46, 184, 114), (26, 188, 156), (52, 152, 219),
    (155, 89, 182), (236, 112, 167), (140, 198, 63), (255, 138, 101),
]
GRADIENT_STOPS = [(0.0, (64, 196, 224)), (0.55, (118, 172, 243)), (1.0, (198, 140, 232))]


def gradient(size: tuple[int, int], stops=GRADIENT_STOPS) -> Image.Image:
    """Vertical multi-stop gradient."""
    import numpy as np

    w, h = size
    t = np.linspace(0, 1, h, dtype=np.float32)
    out = np.zeros((h, 3), dtype=np.float32)
    for ch in range(3):
        out[:, ch] = np.interp(t, [s[0] for s in stops], [s[1][ch] for s in stops])
    arr = np.repeat(out[:, None, :], w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def sunburst(img: Image.Image, center: tuple[float, float], rays: int = 20, alpha: int = 38) -> None:
    """Faint alternating light wedges radiating from `center`, drawn over the whole image."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    R = max(img.size) * 1.5
    cx, cy = center
    step = 2 * math.pi / rays
    for i in range(0, rays, 2):
        a0, a1 = i * step, (i + 1) * step
        d.polygon([(cx, cy), (cx + R * math.cos(a0), cy + R * math.sin(a0)),
                   (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=(255, 255, 255, alpha))
    img.paste(ov, (0, 0), ov)


def _hits(x: float, y: float, r: float, avoid) -> bool:
    return any(x + r > a[0] and x - r < a[2] and y + r > a[1] and y - r < a[3] for a in avoid)


def snowflake(d: ImageDraw.ImageDraw, cx: float, cy: float, r: float, fill, width: int) -> None:
    for k in range(6):
        ang = k * math.pi / 3
        ex, ey = cx + r * math.cos(ang), cy + r * math.sin(ang)
        d.line([cx, cy, ex, ey], fill=fill, width=width)
        for frac in (0.55, 0.8):  # little branches
            bx, by = cx + r * frac * math.cos(ang), cy + r * frac * math.sin(ang)
            for s in (-1, 1):
                a2 = ang + s * math.pi / 4
                d.line([bx, by, bx + r * 0.26 * math.cos(a2), by + r * 0.26 * math.sin(a2)], fill=fill, width=max(2, width - 1))
    d.ellipse([cx - width, cy - width, cx + width, cy + width], fill=fill)


def snowflakes(img: Image.Image, rnd: random.Random, n: int, avoid=(), sizes=(40, 130)) -> None:
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    W, H = img.size
    for _ in range(n):
        for _try in range(10):
            r = rnd.uniform(*sizes)
            x, y = rnd.uniform(0, W), rnd.uniform(0, H)
            if not _hits(x, y, r, avoid):
                snowflake(d, x, y, r, (255, 255, 255, rnd.choice([150, 190, 230])), max(3, int(r / 14)))
                break
    img.paste(ov, (0, 0), ov)


def confetti(img: Image.Image, rnd: random.Random, n: int, avoid=()) -> None:
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    W, H = img.size
    for _ in range(n):
        for _try in range(10):
            x, y, r = rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(16, 34)
            if _hits(x, y, r * 2, avoid):
                continue
            col = rnd.choice(FUN_COLORS) + (235,)
            kind = rnd.choice(["dot", "bar", "bar", "ring", "squig"])
            if kind == "dot":
                d.ellipse([x - r / 2, y - r / 2, x + r / 2, y + r / 2], fill=col)
            elif kind == "ring":
                d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=max(4, int(r / 4)))
            elif kind == "bar":
                a = rnd.uniform(0, math.pi)
                dx, dy = math.cos(a) * r * 1.4, math.sin(a) * r * 1.4
                d.line([x - dx, y - dy, x + dx, y + dy], fill=col, width=max(8, int(r / 2)))
            else:  # squiggle
                pts = [(x + i * r / 2, y + math.sin(i * 1.3) * r / 2) for i in range(-4, 5)]
                d.line(pts, fill=col, width=max(6, int(r / 3)), joint="curve")
            break
    img.paste(ov, (0, 0), ov)


def bouncy_line(img: Image.Image, text: str, font: ImageFont.FreeTypeFont, cx: float, top: float, colors,
                rng: random.Random, stroke: int = 9, halo: int = 12, bounce: float = 14, tilt: float = 5,
                spacing: int = 4) -> float:
    """Draw `text` as separate, slightly rotated and bouncing letters, each a different color, with a
    navy outline, white sticker halo and soft shadow. Returns the y of the bottom of the line."""
    advs = [font.getlength(ch) + spacing for ch in text]
    x = cx - sum(advs) / 2
    asc, desc = font.getmetrics()
    pad = stroke + halo + 14
    shadows, halos, faces = [], [], []
    ci = 0
    for i, ch in enumerate(text):
        adv = advs[i]
        if ch != " ":
            size = (int(adv) + 2 * pad, asc + desc + 2 * pad)
            ang = rng.uniform(-tilt, tilt)
            lift = math.sin(i * 1.4) * bounce

            def tile(draw_fn):
                t = Image.new("RGBA", size, (0, 0, 0, 0))
                draw_fn(ImageDraw.Draw(t))
                return t.rotate(ang, resample=Image.BICUBIC, expand=True)

            col = colors[ci % len(colors)]
            ci += 1
            halo_t = tile(lambda dd: dd.text((pad, pad), ch, font=font, fill=WHITE, stroke_width=stroke + halo, stroke_fill=WHITE))
            face_t = tile(lambda dd: dd.text((pad, pad), ch, font=font, fill=col, stroke_width=stroke, stroke_fill=NAVY))
            sh = Image.new("RGBA", halo_t.size, NAVY + (0,))
            sh.putalpha(halo_t.getchannel("A").filter(ImageFilter.GaussianBlur(7)).point(lambda v: int(v * 0.38)))
            px_, py_ = x + adv / 2, top + (asc + desc) / 2 + lift
            pos = (round(px_ - halo_t.width / 2), round(py_ - halo_t.height / 2))
            shadows.append((sh, (pos[0] + 8, pos[1] + 12)))
            halos.append((halo_t, pos))
            faces.append((face_t, pos))
        x += adv
    for layer in (shadows, halos, faces):  # halos before faces so neighbours never cut into a letter
        for t, pos in layer:
            img.paste(t, pos, t)
    return top + asc + desc


def starburst(lines, radius: int, fill=SUN, font_path: str = "", points: int = 18, scale: int = 2) -> Image.Image:
    """RGBA starburst badge with centered text. `lines` = [(text, relative_size), ...] (first is biggest)."""
    S = scale
    R = radius * S
    size = int(R * 2 + 60 * S)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    pts = []
    for i in range(points * 2):
        r = R if i % 2 == 0 else R * 0.84
        a = math.pi * i / points
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=fill, outline=NAVY, width=7 * S)
    inner = [(c + (p[0] - c) * 0.9, c + (p[1] - c) * 0.9) for p in pts]
    d.line(inner + [inner[0]], fill=WHITE, width=4 * S, joint="curve")
    fonts = [ImageFont.truetype(font_path, int(radius * rel * S)) for _, rel in lines]
    heights = [f.getmetrics()[0] + f.getmetrics()[1] for f in fonts]
    y = c - sum(heights) / 2 - radius * 0.02 * S
    for (txt, _), f, h in zip(lines, fonts, heights):
        w = d.textlength(txt, font=f)
        d.text((c - w / 2, y), txt, font=f, fill=NAVY, stroke_width=0)
        y += h * 0.95
    return im.resize((size // S, size // S), Image.LANCZOS)


def ribbon(text: str, font: ImageFont.FreeTypeFont, color=CORAL, pad_x: int = 90, scale: int = 2) -> Image.Image:
    """RGBA banner with swallowtail ends and outlined white text."""
    tmp = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    tw = int(tmp.textlength(text, font=font))
    asc, desc = font.getmetrics()
    th = asc + desc
    h = th + 56
    tail = int(h * 0.55)
    W = tw + 2 * pad_x + 2 * tail + 40
    H = h + 50
    S = scale
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    dark = tuple(int(c * 0.72) for c in color)
    y0 = 10 * S
    for side in (-1, 1):  # back tails, slightly lower and darker
        xb = (W / 2 + side * (tw / 2 + pad_x)) * S
        xo = xb + side * tail * S
        d.polygon([(xb, (y0 + 22 * S)), (xo, (y0 + 22 * S)), (xo - side * tail * 0.35 * S, y0 + 22 * S + h * S / 2), (xo, y0 + 22 * S + h * S),
                   (xb, y0 + 22 * S + h * S)], fill=dark, outline=NAVY, width=5 * S)
    x0, x1 = (W / 2 - tw / 2 - pad_x) * S, (W / 2 + tw / 2 + pad_x) * S
    d.rounded_rectangle([x0, y0, x1, y0 + h * S], radius=14 * S, fill=color, outline=NAVY, width=6 * S)
    d.text((W / 2 * S - tw * S / 2, y0 + 28 * S), text, font=ImageFont.truetype(font.path, font.size * S), fill=WHITE,
           stroke_width=3 * S, stroke_fill=NAVY)
    return im.resize((W, H), Image.LANCZOS)


def framed(panel: Image.Image, border: int = 14, shadow: int = 22, angle: float = 0.0) -> Image.Image:
    """Panel with a navy outline and a soft offset shadow, optionally rotated (RGBA out)."""
    pw, ph = panel.size
    m = shadow + 30
    canvas = Image.new("RGBA", (pw + 2 * m, ph + 2 * m), (0, 0, 0, 0))
    mask = Image.new("L", panel.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1], radius=90, fill=255)
    sh = Image.new("RGBA", canvas.size, NAVY + (0,))
    sh_alpha = Image.new("L", canvas.size, 0)
    sh_alpha.paste(mask.point(lambda v: int(v * 0.35)), (m + shadow, m + shadow))
    sh.putalpha(sh_alpha.filter(ImageFilter.GaussianBlur(10)))
    canvas.alpha_composite(sh)
    canvas.alpha_composite(panel, (m, m))
    ImageDraw.Draw(canvas).rounded_rectangle([m, m, m + pw - 1, m + ph - 1], radius=90, outline=NAVY, width=border)
    return canvas.rotate(angle, resample=Image.BICUBIC, expand=True) if angle else canvas


def circle_sticker(content: Image.Image, diameter: int, angle: float = 0.0, bg=(255, 250, 225)) -> Image.Image:
    """Round sticker: content centered on a pale disc with a white border and navy outline."""
    S = 2
    D = diameter * S
    pad = 18 * S
    im = Image.new("RGBA", (D + 2 * pad, D + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, D + 2 * pad - 1, D + 2 * pad - 1], fill=WHITE, outline=NAVY, width=7 * S)
    d.ellipse([pad, pad, pad + D - 1, pad + D - 1], fill=bg)
    inner = int(D * 0.86)
    c = content.copy()
    c.thumbnail((inner, inner), Image.LANCZOS)
    im.paste(c, (pad + (D - c.width) // 2, pad + (D - c.height) // 2))
    d.ellipse([pad, pad, pad + D - 1, pad + D - 1], outline=NAVY, width=4 * S)
    im = im.resize((im.width // S, im.height // S), Image.LANCZOS)
    return im.rotate(angle, resample=Image.BICUBIC, expand=True) if angle else im
