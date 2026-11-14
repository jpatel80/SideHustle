"""Tests for scripts/build_interior.py. Run: python3 -m unittest discover -s tests -v"""
import contextlib
import importlib.util
import io
import math
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader

SPEC = importlib.util.spec_from_file_location(
    "build_interior", Path(__file__).resolve().parent.parent / "scripts" / "build_interior.py"
)
bi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bi)


def flower(path: Path, petals: int, size=(1792, 2304), shade=False, solid=False, border=False):
    """Synthetic anti-aliased line art. Drawn 2x then downsampled so edges are gray, like real AI output."""
    w, h = size[0] * 2, size[1] * 2
    im = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(im)
    cx, cy, r = w // 2, h // 2, min(w, h) // 5
    for i in range(petals):
        a = 2 * math.pi * i / petals
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        d.ellipse([px - r // 2, py - r // 2, px + r // 2, py + r // 2], outline=0, width=14)
    d.ellipse([cx - r // 3, cy - r // 3, cx + r // 3, cy + r // 3], outline=0, width=14)
    if shade:
        d.rectangle([w // 8, h // 8, w * 3 // 4, h // 2], fill=140)
    if solid:
        d.rectangle([0, 0, w, int(h * 0.8)], fill=0)
    if border:
        d.rectangle([2, 2, w - 3, h - 3], outline=0, width=10)
    im = im.resize(size, Image.LANCZOS)
    im.save(path)


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = bi.main(argv)
    return code, out.getvalue(), err.getvalue()


class BuildInteriorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.imgs = self.dir / "pages"
        self.imgs.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def make(self, n):
        for i in range(n):
            flower(self.imgs / f"page_{i + 1:02d}.png", petals=5 + i)

    def build(self, *extra, n=None):
        out = self.dir / "interior.pdf"
        code, so, se = run(["build", str(self.imgs), "-o", str(out), "--title", "Test Book",
                            "--author", "Paperkite Studio", *extra])
        return code, out, so, se

    def test_natural_sort(self):
        names = ["p10.png", "p2.png", "p1.png"]
        got = sorted((Path(n) for n in names), key=bi.natural_key)
        self.assertEqual([p.name for p in got], ["p1.png", "p2.png", "p10.png"])

    def test_gutter_table(self):
        self.assertEqual(bi.gutter_for(24), 0.375)
        self.assertEqual(bi.gutter_for(150), 0.375)
        self.assertEqual(bi.gutter_for(151), 0.5)
        self.assertEqual(bi.gutter_for(828), 0.875)
        with self.assertRaises(ValueError):
            bi.gutter_for(829)

    def test_build_page_count_and_size_no_bleed(self):
        self.make(12)  # 4 front + 24 + test page leaf = 30 pages
        code, out, so, se = self.build()
        self.assertEqual(code, 0, se)
        r = PdfReader(str(out))
        self.assertEqual(len(r.pages), 30)
        self.assertEqual(len(r.pages) % 2, 0)
        for p in r.pages:
            self.assertAlmostEqual(float(p.mediabox.width), 8.5 * 72, places=1)
            self.assertAlmostEqual(float(p.mediabox.height), 11 * 72, places=1)

    def test_build_bleed_size(self):
        self.make(12)
        code, out, so, se = self.build("--bleed")
        self.assertEqual(code, 0, se)
        r = PdfReader(str(out))
        self.assertAlmostEqual(float(r.pages[0].mediabox.width), (8.5 + 0.125) * 72, places=1)
        self.assertAlmostEqual(float(r.pages[0].mediabox.height), (11 + 0.25) * 72, places=1)

    def test_imprint_on_title_and_copyright_pages(self):
        self.make(10)
        out = self.dir / "int.pdf"
        code, _, err = run(["build", str(self.imgs), "-o", str(out), "--title", "T", "--author", "A B",
                            "--imprint", "Little Fox Paper Co", "--note", "Made with AI tools."])
        self.assertEqual(code, 0, err)
        r = PdfReader(str(out))
        self.assertIn("Little Fox Paper Co", r.pages[0].extract_text())
        self.assertIn("Little Fox Paper Co", r.pages[1].extract_text())
        self.assertIn("Made with AI tools.", r.pages[1].extract_text())

    def test_too_few_pages_is_refused(self):
        self.make(3)  # 4 + 6 + 2 = 12 pages
        code, out, so, se = self.build()
        self.assertEqual(code, 2)
        self.assertIn("at least 24", se)
        self.assertFalse(out.exists())

    def test_pad_to_min(self):
        self.make(3)
        code, out, so, se = self.build("--pad-to-min")
        self.assertEqual(code, 0, se)
        r = PdfReader(str(out))
        self.assertEqual(len(r.pages), 24)
        self.assertIn("Color test page", r.pages[22].extract_text())  # still on the last leaf

    def test_art_is_pure_black_and_white(self):
        self.make(12)
        code, out, so, se = self.build()
        self.assertEqual(code, 0, se)
        page = PdfReader(str(out)).pages[4]  # first art page (p5)
        imgs = list(page.images)
        self.assertEqual(len(imgs), 1)
        im = imgs[0].image.convert("L")
        hist = im.histogram()
        self.assertEqual(sum(hist[1:255]), 0, "art should contain only 0 and 255")
        self.assertGreater(hist[0], 0)

    def test_art_stays_inside_margins(self):
        self.make(12)
        code, out, so, se = self.build()
        self.assertEqual(code, 0, se)
        page = PdfReader(str(out)).pages[4]
        pw, ph = float(page.mediabox.width), float(page.mediabox.height)
        # image placement is in the content stream's cm operator; decode via text search
        content = page.get_contents().get_data().decode("latin-1")
        import re

        m = re.search(r"q\s+([\d.]+) 0 0 ([\d.]+) ([\d.]+) ([\d.]+) cm", content)
        self.assertIsNotNone(m, content[:200])
        w, h, x, y = map(float, m.groups())
        gutter = bi.gutter_for(28) * 72
        outer = 0.375 * 72
        self.assertGreaterEqual(x, gutter - 0.5)           # recto: gutter on the left
        self.assertLessEqual(x + w, pw - outer + 0.5)
        self.assertGreaterEqual(y, 0.375 * 72 - 0.5)
        self.assertLessEqual(y + h, ph - 0.375 * 72 + 0.5)

    def test_blank_backs_are_blank(self):
        self.make(12)
        code, out, so, se = self.build()
        self.assertEqual(code, 0, se)
        r = PdfReader(str(out))
        for i in range(5, 28, 2):  # verso pages behind each art page (p6, p8, ...)
            self.assertEqual(len(list(r.pages[i].images)), 0)
            self.assertEqual(r.pages[i].extract_text().strip(), "")

    def test_fonts_embedded(self):
        self.make(12)
        code, out, so, se = self.build()
        self.assertEqual(code, 0, se)
        self.assertIn('"fonts_embedded": true', so)

    def test_qa_flags_bad_pages(self):
        flower(self.imgs / "a_clean.png", 6)
        flower(self.imgs / "b_shaded.png", 7, shade=True)
        flower(self.imgs / "c_solid.png", 8, solid=True)
        flower(self.imgs / "d_bordered.png", 9, border=True)
        flower(self.imgs / "e_clean_dup.png", 6)
        flower(self.imgs / "f_small.png", 10, size=(600, 800))
        code, so, se = run(["qa", str(self.imgs)])
        self.assertEqual(code, 0)
        by_file = {}
        cur = None
        for line in so.splitlines():
            if line.startswith("  ") and not line.startswith("    "):
                cur = line.strip()
                by_file[cur] = []
            elif line.startswith("    - ") and cur:
                by_file[cur].append(line.strip()[2:])
        joined = lambda f: " | ".join(by_file.get(f, []))
        self.assertIn("gray", joined("b_shaded.png"))
        self.assertIn("ink", joined("c_solid.png"))
        self.assertIn("edge", joined("d_bordered.png"))
        self.assertIn("low resolution", joined("f_small.png"))
        self.assertIn("near-duplicate", joined("a_clean.png"))
        self.assertIn("near-duplicate", joined("e_clean_dup.png"))
        self.assertNotIn("b_shaded.png", " ".join(by_file.get("c_solid.png", [])))

    def test_copyright_page_claims_only_arrangement_and_states_ai(self):
        self.make(10)
        out = self.dir / "c.pdf"
        code, _, err = run(["build", str(self.imgs), "-o", str(out), "--title", "T", "--author", "A B",
                            "--imprint", "Little Fox Paper Co", "--year", "2026"])
        self.assertEqual(code, 0, err)
        text = " ".join(PdfReader(str(out)).pages[1].extract_text().split())
        self.assertIn("Selection, arrangement and design \u00a9 2026 Little Fox Paper Co.", text)
        self.assertIn("generated with AI image tools", text)
        self.assertNotIn("All rights reserved", text)
        self.assertNotIn("with the help of", text)

    def test_test_page_is_last_leaf_and_can_be_skipped(self):
        self.make(12)
        code, out, so, se = self.build()
        r = PdfReader(str(out))
        self.assertIn("Color test page", r.pages[28].extract_text())
        self.assertEqual(r.pages[29].extract_text().strip(), "")
        code, out, so, se = self.build("--no-test-page")
        self.assertEqual(len(PdfReader(str(out)).pages), 28)

    def test_title_page_shows_a_picture_and_keeps_coloring_book_together(self):
        self.assertEqual(bi.split_title("Cozy Winter Animals Coloring Book"), ["Cozy Winter Animals", "Coloring Book"])
        self.assertEqual(bi.split_title("Cozy Cottage Coloring Book for Adults"),
                         ["Cozy Cottage", "Coloring Book", "for Adults"])
        self.assertEqual(bi.split_title("Garden Friends"), ["Garden Friends"])
        self.make(12)
        code, out, so, se = self.build()
        self.assertEqual(len(list(PdfReader(str(out)).pages[0].images)), 1)
        code, out, so, se = self.build("--title-art", "0")
        self.assertEqual(len(list(PdfReader(str(out)).pages[0].images)), 0)

    def test_default_gutter_and_art_resolution(self):
        self.make(12)
        code, out, so, se = self.build()
        self.assertIn('"gutter_in": 0.5', so)
        self.assertIn('"art_dpi": 600', so)
        page = PdfReader(str(out)).pages[4]
        im = list(page.images)[0].image
        self.assertGreater(im.width, 3600)  # about 7.6 in at 600 DPI
        code, out, so, se = self.build("--gutter", "0.1")  # never below KDP's minimum
        self.assertIn('"gutter_in": 0.375', so)

    def test_page_limit_depends_on_trim(self):
        self.assertEqual(bi.max_pages_for((8.5, 11.0)), 590)
        self.assertEqual(bi.max_pages_for((6.0, 9.0)), 828)

    def test_qa_real_size_pages_are_not_flagged_low_resolution(self):
        flower(self.imgs / "a.png", 6, size=(1152, 1536))
        code, so, se = run(["qa", str(self.imgs)])
        self.assertIn("1 clean, 0 flagged", so)

    def test_qa_fine_lines_are_not_gray_shading(self):
        # many thin anti-aliased lines: lots of mid-gray edge pixels but no flat gray area
        im = Image.new("L", (2304, 3072), 255)
        d = ImageDraw.Draw(im)
        for x in range(200, 2100, 24):
            d.line([x, 300, x + 60, 2700], fill=0, width=5)
        im.resize((1152, 1536), Image.LANCZOS).save(self.imgs / "fine.png")
        r = bi.analyse_image(self.imgs / "fine.png", "adult")
        self.assertFalse([f for f in r["flags"] if "gray" in f], r["flags"])

    def test_qa_flags_crackly_detail_and_odd_line_weight(self):
        import random
        rnd = random.Random(1)
        im = Image.new("L", (1152, 1536), 255)
        d = ImageDraw.Draw(im)
        for _ in range(900):  # hundreds of tiny closed rings = areas nobody can color
            x, y = rnd.randrange(60, 1090), rnd.randrange(60, 1470)
            d.ellipse([x, y, x + 9, y + 9], outline=0, width=2)
        im.save(self.imgs / "noisy.png")
        r = bi.analyse_image(self.imgs / "noisy.png", "kids")
        self.assertTrue([f for f in r["flags"] if "crackly" in f], r)
        for i in range(5):
            flower(self.imgs / f"bold_{i}.png", 5 + i, size=(1152, 1536))
        thin = Image.new("L", (1152, 1536), 255)
        ImageDraw.Draw(thin).ellipse([200, 300, 950, 1200], outline=0, width=2)
        thin.save(self.imgs / "thin.png")
        res = {r["file"]: r for r in bi.run_qa(bi.list_images(self.imgs))}
        self.assertTrue([f for f in res["thin.png"]["flags"] if "line weight" in f], res["thin.png"])

    def test_qa_against_other_books_catches_repeats(self):
        other = self.dir / "otherbook" / "final" / "pages"
        other.mkdir(parents=True)
        flower(other / "01.png", 6, size=(1152, 1536))
        flower(self.imgs / "same.png", 6, size=(1152, 1536))
        flower(self.imgs / "different.png", 11, size=(1152, 1536))
        code, so, se = run(["qa", str(self.imgs), "--against", str(other)])
        self.assertIn("another book's page: otherbook/01.png", so)

    def test_qa_strict_exit_code(self):
        flower(self.imgs / "a.png", 6, shade=True)
        code, so, se = run(["qa", str(self.imgs), "--strict"])
        self.assertEqual(code, 1)

    def test_cover_dims(self):
        code, so, se = run(["cover-dims", "--pages", "100", "--trim", "8.5x11"])
        self.assertEqual(code, 0)
        self.assertIn('"spine_in": 0.2252', so)
        # 2 x 8.5 trim + 0.2252 spine + 2 x 0.125 bleed = 17.4752; 11 + 0.25 bleed = 11.25
        self.assertIn('"full_cover_in": [\n    17.4752,\n    11.25\n  ]', so)


if __name__ == "__main__":
    unittest.main()
