"""Tests for scripts/make_cover.py. Run: python3 -m unittest discover -s tests -v"""
import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("make_cover", ROOT / "scripts" / "make_cover.py")
mc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mc)
fun = mc.fun


def art(path: Path):
    im = Image.new("L", (1152, 1536), 255)
    d = ImageDraw.Draw(im)
    d.ellipse([200, 300, 950, 1200], outline=0, width=14)
    d.ellipse([400, 600, 500, 700], outline=0, width=10)
    im.save(path)


def boxes(path: Path):
    """Three side-by-side closed boxes on white, thick black lines (adjacent regions across a line)."""
    im = Image.new("L", (900, 600), 255)
    d = ImageDraw.Draw(im)
    for i in range(3):
        d.rectangle([60 + i * 260, 100, 60 + (i + 1) * 260, 500], outline=0, width=12)
    d.ellipse([140, 240, 170, 270], fill=255, outline=0, width=0)  # tiny highlight-sized region stays uncolored
    im.save(path)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = mc.main(argv)
    return code, out.getvalue(), err.getvalue()


class CoverTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.art = self.dir / "art.png"
        art(self.art)

    def tearDown(self):
        self._tmp.cleanup()

    def build(self, pages, name="cover.pdf", extra=()):
        out = self.dir / name
        code, stdout, err = run([str(self.art), "-o", str(out), "--title", "Cozy Winter Animals Coloring Book",
                                 "--subtitle", "30 Bold and Easy Pictures for Kids Ages 4-8",
                                 "--author", "Wren Ashby", "--imprint", "Little Fox Paper Co",
                                 "--pages", str(pages), "--blurb", "One line.|Second line.", *extra])
        self.assertEqual(code, 0, err)
        return out

    def test_geometry_matches_kdp_formula(self):
        g = mc.cover_geometry(64, (8.5, 11.0))
        self.assertAlmostEqual(g["spine"], 64 * 0.002252, places=6)
        self.assertAlmostEqual(g["total_w"], 0.125 + 8.5 + g["spine"] + 8.5 + 0.125, places=6)
        self.assertAlmostEqual(g["total_h"], 11.25, places=6)

    def test_geometry_matches_cover_dims_command(self):
        # same numbers as build_interior's cover-dims (single source of truth)
        g = mc.cover_geometry(64, (8.5, 11.0))
        self.assertEqual(round(g["total_w"], 4), 17.3941)

    def test_spine_text_only_from_80_pages(self):
        self.assertFalse(mc.cover_geometry(64, (8.5, 11.0))["spine_text"])
        self.assertFalse(mc.cover_geometry(79, (8.5, 11.0))["spine_text"])
        self.assertTrue(mc.cover_geometry(80, (8.5, 11.0))["spine_text"])

    def test_pdf_is_one_page_with_exact_size(self):
        out = self.build(64)
        r = PdfReader(str(out))
        self.assertEqual(len(r.pages), 1)
        g = mc.cover_geometry(64, (8.5, 11.0))
        self.assertAlmostEqual(float(r.pages[0].mediabox.width) / 72, g["total_w"], places=2)
        self.assertAlmostEqual(float(r.pages[0].mediabox.height) / 72, g["total_h"], places=2)

    def test_png_pixel_size_is_300dpi(self):
        out = self.build(64)
        im = Image.open(out.with_suffix(".png"))
        g = mc.cover_geometry(64, (8.5, 11.0))
        self.assertEqual(im.size, (round(g["total_w"] * 300), round(g["total_h"] * 300)))

    def test_barcode_area_is_pure_white_and_clear_of_edges(self):
        out = self.build(64)
        g = mc.cover_geometry(64, (8.5, 11.0))
        x0, y0, x1, y1 = barcode_px = [round(v * 300) for v in mc.barcode_box(g)]
        im = Image.open(out.with_suffix(".png")).convert("RGB")
        self.assertEqual(im.crop((x0, y0, x1, y1)).getextrema(), ((255, 255), (255, 255), (255, 255)))
        bx0, by0, bx1, by1 = mc.barcode_box(g)
        self.assertAlmostEqual(bx1 - bx0, 2.0, places=3)
        self.assertAlmostEqual(by1 - by0, 1.2, places=3)
        self.assertGreaterEqual(g["back_x1"] - bx1, 0.25)  # from the spine
        self.assertGreaterEqual(g["bottom"] - by1, 0.25)  # from the trim edge

    def test_spine_is_blank_when_under_minimum(self):
        out = self.build(64)
        g = mc.cover_geometry(64, (8.5, 11.0))
        im = Image.open(out.with_suffix(".png")).convert("RGB")
        strip = im.crop((round(g["spine_x0"] * 300), 0, round(g["spine_x1"] * 300), im.height))
        dark = sum(1 for p in strip.getdata() if sum(p) < 300)  # navy text would be dark
        self.assertEqual(dark, 0)

    def test_spine_has_text_when_allowed(self):
        out = self.build(100, name="c100.pdf")
        g = mc.cover_geometry(100, (8.5, 11.0))
        im = Image.open(out.with_suffix(".png")).convert("RGB")
        strip = im.crop((round(g["spine_x0"] * 300), 0, round(g["spine_x1"] * 300), im.height))
        dark = sum(1 for p in strip.getdata() if p[0] < 90 and p[2] < 140)
        self.assertGreater(dark, 500)

    def test_front_text_stays_inside_safe_area(self):
        out = self.build(64)
        g = mc.cover_geometry(64, (8.5, 11.0))
        im = Image.open(out.with_suffix(".png")).convert("RGB")
        # nothing dark (text or line art) in the 0.25 in strip next to the trim edge
        edge = round(0.25 * 300)
        right = round(g["front_x1"] * 300)
        top = round(g["top"] * 300)
        for box in ((right - edge, 0, right, im.height), (round(g["front_x0"] * 300), top, round(g["front_x0"] * 300) + 2, top + 10)):
            region = im.crop(box)
            self.assertEqual(sum(1 for p in region.getdata() if sum(p) < 200), 0)

    def test_title_lines(self):
        self.assertEqual(mc.title_lines("Cozy Winter Animals Coloring Book"), ["Cozy Winter", "Animals", "Coloring Book"])
        self.assertEqual(mc.title_lines("Garden Friends"), ["Garden", "Friends"])
        self.assertEqual(mc.title_lines("Mandalas"), ["Mandalas"])

    def test_colorize_fills_regions_and_keeps_lines(self):
        src = self.dir / "boxes.png"
        boxes(src)
        img, tip, crayon = mc.colorize_half(Image.open(src), seed=1, split=2.0, tilt=0.0, jitter=False)
        px_ = img.load()
        for cx in (190, 450, 710):  # box centers are filled with a saturated color
            r, g, b = px_[cx, 300]
            self.assertGreater(max(r, g, b) - min(r, g, b), 40)
        self.assertEqual(px_[5, 5], (255, 255, 255))  # outside background stays white
        self.assertLess(sum(px_[66, 300]), 100)  # the black line is still black
        self.assertEqual(len(tip), 2)
        self.assertEqual(len(crayon), 3)

    def test_colorize_neighbouring_regions_get_different_colors(self):
        src = self.dir / "boxes.png"
        boxes(src)
        img, _, _ = mc.colorize_half(Image.open(src), seed=5, split=2.0, tilt=0.0, jitter=False)
        colors = [img.getpixel((cx, 300))[:3] for cx in (190, 450, 710)]
        self.assertNotEqual(colors[0], colors[1])
        self.assertNotEqual(colors[1], colors[2])

    def test_colorize_half_leaves_the_other_side_black_and_white(self):
        src = self.dir / "boxes.png"
        boxes(src)
        img, _, _ = mc.colorize_half(Image.open(src), seed=2, split=0.5, tilt=0.0, jitter=False)
        a = img.convert("RGB")
        left_colored = any(max(p) - min(p) > 40 for p in a.crop((0, 0, 400, 600)).getdata())
        right_colored = any(max(p) - min(p) > 8 for p in a.crop((520, 0, 900, 600)).getdata())
        self.assertTrue(left_colored)
        self.assertFalse(right_colored)

    def test_colorize_is_deterministic_per_seed(self):
        src = self.dir / "boxes.png"
        boxes(src)
        a, _, _ = mc.colorize_half(Image.open(src), seed=9)
        b, _, _ = mc.colorize_half(Image.open(src), seed=9)
        self.assertEqual(list(a.getdata())[::997], list(b.getdata())[::997])

    def test_colored_half_cover_builds_and_keeps_barcode_white(self):
        out = self.build(64, name="cc.pdf", extra=("--colored-half",))
        g = mc.cover_geometry(64, (8.5, 11.0))
        im = Image.open(out.with_suffix(".png")).convert("RGB")
        x0, y0, x1, y1 = (round(v * 300) for v in mc.barcode_box(g))
        self.assertEqual(im.crop((x0, y0, x1, y1)).getextrema(), ((255, 255), (255, 255), (255, 255)))

    def test_plain_style_still_builds_with_blank_barcode(self):
        out = self.build(64, name="plain.pdf", extra=("--style", "plain"))
        g = mc.cover_geometry(64, (8.5, 11.0))
        im = Image.open(out.with_suffix(".png")).convert("RGB")
        self.assertEqual(im.getpixel((10, 10)), mc.BG)
        x0, y0, x1, y1 = (round(v * 300) for v in mc.barcode_box(g))
        self.assertEqual(im.crop((x0, y0, x1, y1)).getextrema(), ((255, 255), (255, 255), (255, 255)))

    def test_fun_style_with_badge_and_stickers(self):
        out = self.build(64, name="fun.pdf", extra=("--badge", "30|BIG PICTURES|TO COLOR!", "--colored-half",
                                                     "--stickers", str(self.art), str(self.art), str(self.art), str(self.art), str(self.art)))
        g = mc.cover_geometry(64, (8.5, 11.0))
        im = Image.open(out.with_suffix(".png")).convert("RGB")
        self.assertEqual(len(PdfReader(str(out)).pages), 1)
        # the fun style is genuinely colorful: many saturated pixels on the front
        front = im.crop((round(g["front_x0"] * 300), 0, round(g["front_x1"] * 300), im.height)).resize((200, 260))
        sat = sum(1 for p in front.getdata() if max(p) - min(p) > 60)
        self.assertGreater(sat, 5000)
        # barcode box still pure white, spine still blank (no dark pixels)
        x0, y0, x1, y1 = (round(v * 300) for v in mc.barcode_box(g))
        self.assertEqual(im.crop((x0, y0, x1, y1)).getextrema(), ((255, 255), (255, 255), (255, 255)))
        strip = im.crop((round(g["spine_x0"] * 300), 0, round(g["spine_x1"] * 300), im.height))
        self.assertEqual(sum(1 for p in strip.getdata() if sum(p) < 300), 0)

    def test_every_theme_builds_with_blank_barcode_and_spine(self):
        g = mc.cover_geometry(64, (8.5, 11.0))
        tops = set()
        for theme in sorted(fun.THEMES):
            out = self.build(64, name=f"{theme}.pdf", extra=("--theme", theme))
            im = Image.open(out.with_suffix(".png")).convert("RGB")
            tops.add(im.getpixel((20, 20)))
            x0, y0, x1, y1 = (round(v * 300) for v in mc.barcode_box(g))
            self.assertEqual(im.crop((x0, y0, x1, y1)).getextrema(), ((255, 255), (255, 255), (255, 255)))
            strip = im.crop((round(g["spine_x0"] * 300), 0, round(g["spine_x1"] * 300), im.height))
            self.assertEqual(sum(1 for p in strip.getdata() if sum(p) < 300), 0, theme)
        self.assertEqual(len(tops), len(fun.THEMES))  # the themes really differ

    def test_spine_text_style_fun_with_enough_pages(self):
        out = self.build(84, name="p84.pdf", extra=("--theme", "garden"))
        g = mc.cover_geometry(84, (8.5, 11.0))
        self.assertTrue(g["spine_text"])
        im = Image.open(out.with_suffix(".png")).convert("RGB")
        strip = im.crop((round(g["spine_x0"] * 300), 0, round(g["spine_x1"] * 300), im.height))
        self.assertGreater(sum(1 for p in strip.getdata() if p[0] < 90 and p[2] < 140), 500)

    def test_missing_sticker_is_an_error(self):
        code, _, err = run([str(self.art), "-o", str(self.dir / "c.pdf"), "--title", "T", "--author", "A", "--pages", "64",
                            "--stickers", str(self.dir / "missing.png")])
        self.assertEqual(code, 2)

    def test_fun_gradient_and_scatter_respect_avoid_zone(self):
        import random
        img = fun.gradient((600, 400))
        self.assertEqual(img.size, (600, 400))
        self.assertNotEqual(img.getpixel((10, 5)), img.getpixel((10, 395)))  # it is a gradient
        before = img.copy()
        avoid = [(200, 0, 400, 400)]
        fun.snowflakes(img, random.Random(1), 40, avoid)
        fun.confetti(img, random.Random(2), 60, avoid)
        self.assertNotEqual(list(img.getdata()), list(before.getdata()))
        self.assertEqual(list(img.crop((205, 0, 395, 400)).getdata()), list(before.crop((205, 0, 395, 400)).getdata()))

    def test_bouncy_line_draws_letters_and_returns_bottom(self):
        import random
        from PIL import ImageFont
        font = ImageFont.truetype(str(mc.FUN_FONT), 120)
        img = Image.new("RGB", (900, 300), (200, 220, 250))
        bottom = fun.bouncy_line(img, "Hello Fun", font, 450, 20, fun.FUN_COLORS, random.Random(0))
        self.assertGreater(bottom, 20 + 100)
        self.assertNotEqual(img.getextrema(), ((200, 200), (220, 220), (250, 250)))

    def test_missing_art_is_an_error(self):
        code, _, err = run([str(self.dir / "nope.png"), "-o", str(self.dir / "c.pdf"), "--title", "T",
                            "--author", "A", "--pages", "64"])
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_page_count_below_kdp_minimum_is_refused(self):
        code, _, err = run([str(self.art), "-o", str(self.dir / "c.pdf"), "--title", "T", "--author", "A", "--pages", "10"])
        self.assertEqual(code, 2)

    def test_guides_image_written(self):
        out = self.build(64)
        self.assertTrue((self.dir / "cover_guides.png").exists())


if __name__ == "__main__":
    unittest.main()
