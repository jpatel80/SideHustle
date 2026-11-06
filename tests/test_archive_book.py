"""Tests for scripts/archive_book.py. Run: python3 -m unittest discover -s tests -v"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas

SPEC = importlib.util.spec_from_file_location("archive_book", Path(__file__).resolve().parent.parent / "scripts" / "archive_book.py")
ab = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ab)


def make_book(root: Path, color_page: bool = False) -> Path:
    book = root / "007-test"
    pages = book / "pages"
    pages.mkdir(parents=True)
    for i in range(3):
        im = Image.new("RGB", (400, 520), (255, 255, 255))
        ImageDraw.Draw(im).ellipse([60, 80, 340, 440], outline=(0, 0, 0), width=8)
        if color_page and i == 1:
            ImageDraw.Draw(im).rectangle([10, 10, 60, 60], fill=(250, 20, 20))
        im.save(pages / f"{i + 1:02d}.png")
    for name in ("interior.pdf", "cover.pdf"):
        c = canvas.Canvas(str(book / name), pagesize=(200, 300))
        c.showPage()
        c.showPage()
        c.save()
    Image.new("RGB", (100, 60), (10, 200, 200)).save(book / "cover.png")
    rows = [{"cost_usd": 0.006}, {"cost_usd": 0.05}]
    (pages / "ledger.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return book


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_archive_copies_everything_and_writes_manifest(self):
        book = make_book(self.root)
        info = ab.archive(book)
        final = book / "final"
        for name in ("interior.pdf", "cover.pdf", "cover_preview.png", "ledger.jsonl", "MANIFEST.md"):
            self.assertTrue((final / name).is_file(), name)
        self.assertEqual(len(list((final / "pages").glob("*.png"))), 3)
        self.assertEqual(info["pages"], 3)
        self.assertEqual(info["interior_pages"], 2)
        self.assertAlmostEqual(info["spend_usd"], 0.056, places=4)
        manifest = (final / "MANIFEST.md").read_text()
        self.assertIn("$0.0560", manifest)
        self.assertIn("interior.pdf", manifest)

    def test_gray_pages_are_stored_losslessly_and_smaller(self):
        book = make_book(self.root)
        ab.archive(book)
        src = Image.open(book / "pages" / "01.png").convert("L")
        dst = Image.open(book / "final" / "pages" / "01.png")
        self.assertEqual(dst.mode, "L")
        self.assertIsNone(__import__("PIL.ImageChops", fromlist=["x"]).difference(src, dst).getbbox())
        self.assertLess((book / "final" / "pages" / "01.png").stat().st_size, (book / "pages" / "01.png").stat().st_size)

    def test_near_gray_noise_is_stored_as_gray(self):
        book = make_book(self.root)
        im = Image.open(book / "pages" / "03.png").convert("RGB")
        px = im.load()
        for x in range(100, 140):  # faint chroma noise like image models leave at line edges
            px[x, 100] = (200, 205, 210)
        im.save(book / "pages" / "03.png")
        ab.archive(book)
        self.assertEqual(Image.open(book / "final" / "pages" / "03.png").mode, "L")

    def test_color_pages_stay_color(self):
        book = make_book(self.root, color_page=True)
        ab.archive(book)
        self.assertEqual(Image.open(book / "final" / "pages" / "02.png").mode, "RGB")
        self.assertEqual(Image.open(book / "final" / "pages" / "01.png").mode, "L")

    def test_rerun_rebuilds_final(self):
        book = make_book(self.root)
        ab.archive(book)
        (book / "final" / "stale.txt").write_text("old")
        ab.archive(book)
        self.assertFalse((book / "final" / "stale.txt").exists())

    def test_missing_inputs_is_an_error(self):
        book = make_book(self.root)
        (book / "cover.pdf").unlink()
        with self.assertRaises(SystemExit):
            ab.archive(book)


if __name__ == "__main__":
    unittest.main()
