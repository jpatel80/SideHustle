"""Tests for scripts/book_factory.py (no network, no spending: pages are synthetic)."""
import importlib.util
import json
import math
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from pypdf import PdfReader

SPEC = importlib.util.spec_from_file_location(
    "book_factory", Path(__file__).resolve().parent.parent / "scripts" / "book_factory.py"
)
bf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bf)

SUBJECTS = [f"A {w} in a garden" for w in
            "rabbit hedgehog teapot wheelbarrow beehive lantern bicycle windmill bridge cottage swing kettle".split()]


def art(path: Path, seed: int):
    """Distinct synthetic line art per page: a few big outlined shapes at seeded positions."""
    import random
    rnd = random.Random(seed * 7919)
    im = Image.new("L", (1152, 1536), 255)
    d = ImageDraw.Draw(im)
    for _ in range(4):
        x, y = rnd.randrange(150, 800), rnd.randrange(150, 1150)
        w, h = rnd.randrange(160, 420), rnd.randrange(160, 420)
        if rnd.random() < 0.5:
            d.ellipse([x, y, x + w, y + h], outline=0, width=9)
        else:
            d.rectangle([x, y, x + w, y + h], outline=0, width=9)
    im.save(path)


def config(**over):
    cfg = {
        "title": "Garden Friends Coloring Book", "subtitle": "12 Bold and Easy Pictures for Kids Ages 3-6",
        "author": "Wren Ashby", "imprint": "Little Fox Paper Co", "audience": "kids", "reading_age": [3, 6],
        "theme": "garden", "badge": "12|BIG PICTURES|TO COLOR!", "cover_art": 1, "stickers": [2, 3, 4, 5, 6],
        "blurb": ["12 garden friends.", "The inside pages are black and white. The colors on the cover are just an example!"],
        "description": "Twelve pictures.<br>The inside pages are printed in black and white.",
        "keywords": [f"garden coloring phrase {i}" for i in range(7)],
        "categories": ["Books > Children's Books > Activities"], "price_usd": 7.99,
    }
    cfg.update(over)
    return cfg


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.books = Path(self._tmp.name) / "books"
        self.book = self.books / "009-garden-friends"
        (self.book / "pages").mkdir(parents=True)
        (self.book / "subjects.txt").write_text("# test\n" + "\n".join(SUBJECTS) + "\n")
        for i, s in enumerate(SUBJECTS, start=1):
            art(self.book / "pages" / f"{i:02d}_{bf.gi.slugify(s)}.png", 4 + i)
        (self.book / "pages" / "ledger.jsonl").write_text(json.dumps({"cost_usd": 0.006}) + "\n")
        self.write(config())
        self.log = []

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, cfg):
        (self.book / "book.json").write_text(json.dumps(cfg))

    def cfg(self):
        return bf.load_config(self.book)

    def test_config_requires_fields(self):
        c = config()
        del c["keywords"]
        self.write(c)
        with self.assertRaises(bf.FactoryError):
            bf.load_config(self.book)

    def test_check_passes_clean_config_with_pricing_warning(self):
        problems, warnings = bf.check(self.book, self.cfg())
        self.assertEqual(problems, [])
        self.assertTrue(any("royalty" in w for w in warnings))

    def test_check_catches_rule_breaks(self):
        cases = {
            "banned term 'frozen'": config(title="Frozen Friends Coloring Book"),
            "banned term 'learn'": config(description="Learn colors. The inside pages are black and white."),
            "exactly 7 keywords": config(keywords=["a", "b"]),
            "characters (KDP limit 50)": config(keywords=["x" * 51] + ["k"] * 6),
            "without the full name": config(imprint="Little Fox"),
            "must not be in the Author field": config(author="Little Fox Paper Co"),
            "blurb must say": config(blurb=["12 garden friends."]),
            "description must say": config(description="Twelve pictures."),
            "badge says 30": config(badge="30|BIG PICTURES"),
            "subtitle says 40": config(subtitle="40 Bold Pictures for Kids Ages 3-6"),
            "below KDP's minimum": config(price_usd=4.99),
        }
        for expect, c in cases.items():
            self.write(c)
            problems, _ = bf.check(self.book, self.cfg())
            self.assertTrue(any(expect in p for p in problems), (expect, problems))

    def test_placeholder_author_is_a_warning(self):
        self.write(config(author="Clara Whitcombe", author_is_placeholder=True))
        _, warnings = bf.check(self.book, self.cfg())
        self.assertTrue(any("placeholder" in w for w in warnings))

    def test_repeated_subjects_across_books(self):
        other = self.books / "001-other"
        other.mkdir()
        (other / "subjects.txt").write_text("A seal balancing a ball on its nose on an iceberg\n")
        got = bf.repeated_subjects(["A smiling seal balancing a ball on its nose", "A happy crab"],
                                   bf.catalog_subjects(self.book))
        self.assertEqual(len(got), 1)
        self.assertIn("001-other", got[0])

    def test_pages_without_images_needs_generate_flag_and_spends_nothing(self):
        for p in (self.book / "pages").glob("0*.png"):
            p.unlink()
        code = bf.cmd_pages(self.book, self.cfg(), generate=False, log=self.log.append)
        self.assertEqual(code, 3)
        self.assertIn("--generate", " ".join(self.log))

    def test_pages_writes_contact_sheets_and_qa(self):
        code = bf.cmd_pages(self.book, self.cfg(), generate=False, log=self.log.append)
        self.assertEqual(code, 0)
        self.assertEqual(len(list((self.book / "review").glob("sheet_*.png"))), 2)
        self.assertEqual(len(json.loads((self.book / "review" / "qa.json").read_text())), 12)

    def test_finish_needs_review_flag(self):
        self.assertEqual(bf.cmd_finish(self.book, self.cfg(), reviewed=False, log=self.log.append), 3)
        self.assertFalse((self.book / "interior.pdf").exists())

    def test_finish_builds_everything_and_restores_in_a_fresh_container(self):
        code = bf.cmd_finish(self.book, self.cfg(), reviewed=True, log=self.log.append)
        self.assertEqual(code, 0, self.log)
        final = self.book / "final"
        n = len(PdfReader(str(final / "interior.pdf")).pages)
        self.assertEqual(n, bf.interior_pages(self.cfg(), 12))
        self.assertEqual(n, 30)
        for name in ("cover.pdf", "cover_preview.png", "MANIFEST.md", "UPLOAD_KIT.md", "ledger.jsonl"):
            self.assertTrue((final / name).is_file(), name)
        kit = (self.book / "listing.md").read_text()
        self.assertEqual(kit, (final / "UPLOAD_KIT.md").read_text())
        for expect in ("| Book title | Garden Friends Coloring Book |", "| Author (first / last name) | Wren Ashby |",
                       "| AI-generated content | **Yes** |", "| $7.99 | 50% | $2.84 | $1.16 |", "| $9.99 | 60% | $2.84 | $3.15 |",
                       "minimum 3, maximum 6", "7. garden coloring phrase 6", "No bleed", "never put Little Fox Paper Co here"):
            self.assertIn(expect, kit)
        # a new session has only final/: `pages` restores the working folder from it
        import shutil
        shutil.rmtree(self.book / "pages")
        self.assertEqual(bf.cmd_pages(self.book, self.cfg(), generate=False, log=self.log.append), 0)
        self.assertEqual(len(bf.page_files(self.book / "pages")), 12)

    def test_finish_stops_on_qa_flags_unless_accepted(self):
        im = Image.new("L", (1152, 1536), 255)
        ImageDraw.Draw(im).rectangle([100, 100, 1000, 1400], fill=120)  # gray fill
        target = sorted((self.book / "pages").glob("03_*.png"))[0]
        im.save(target)
        self.assertEqual(bf.cmd_finish(self.book, self.cfg(), reviewed=True, log=self.log.append), 2)
        self.assertIn("mechanical QA still flags", " ".join(self.log))
        self.assertEqual(bf.cmd_finish(self.book, self.cfg(), reviewed=True, accept_flags="test", log=self.log.append), 0)
        self.assertIn("QA note", (self.book / "listing.md").read_text())

    def test_total_spend_reads_ledgers_and_other_spend(self):
        self.assertAlmostEqual(bf.total_spend(self.books), 0.006)
        t = self.books.parent / "tracking"
        t.mkdir()
        (t / "other_spend.json").write_text(json.dumps([{"what": "bake-off", "usd": 0.68}]))
        self.assertAlmostEqual(bf.total_spend(self.books), 0.686)


if __name__ == "__main__":
    unittest.main()
