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
        self.make(12)  # 4 front + 24 = 28 pages
        code, out, so, se = self.build()
        self.assertEqual(code, 0, se)
        r = PdfReader(str(out))
        self.assertEqual(len(r.pages), 28)
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
        self.make(3)  # 4 + 6 = 10 pages
        code, out, so, se = self.build()
        self.assertEqual(code, 2)
        self.assertIn("at least 24", se)
        self.assertFalse(out.exists())

    def test_pad_to_min(self):
        self.make(3)
        code, out, so, se = self.build("--pad-to-min")
        self.assertEqual(code, 0, se)
        self.assertEqual(len(PdfReader(str(out)).pages), 24)

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
