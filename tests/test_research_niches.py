"""Tests for scripts/research_niches.py (no network: the fetch function is replaced)."""
import contextlib
import csv
import datetime
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "research_niches", Path(__file__).resolve().parent.parent / "scripts" / "research_niches.py"
)
rn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rn)

TODAY = datetime.date(2026, 11, 14)


def fill(path: Path, keyword: str, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rn.WORKSHEET_COLUMNS)
        w.writeheader()
        for i, r in enumerate(rows, start=1):
            w.writerow({"keyword": keyword, "position": i, "title": f"Book {i}", **r})


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_harvest_queries_seed_and_expansions_once_and_waits(self):
        calls, sleeps = [], []
        data = rn.harvest(["cozy coloring book", "cozy coloring book"], True, 0.5, sess=object(),
                          sleep=sleeps.append, fetch=lambda s, p: calls.append(p) or [p + " x"])
        self.assertEqual(len(calls), 27)  # seed + a-z, the duplicate seed is not asked twice
        self.assertEqual(calls[0], "cozy coloring book")
        self.assertEqual(calls[1], "cozy coloring book a")
        self.assertEqual(sleeps, [0.5] * 27)
        self.assertEqual(data["queries"]["cozy coloring book z"], ["cozy coloring book z x"])

    def test_parse_suggestions(self):
        payload = {"suggestions": [{"value": "bold and easy coloring book "}, {"value": ""}, {"other": 1}]}
        self.assertEqual(rn.parse_suggestions(payload), ["bold and easy coloring book"])

    def test_short_prefix_and_high_position_score_more(self):
        data = {"queries": {"coloring book": ["coloring book for adults", "coloring book for kids"],
                            "coloring book for kids ages 4-": ["coloring book for kids ages 4-8"]}}
        s = rn.demand_scores(data)
        self.assertGreater(s["coloring book for adults"]["score"], s["coloring book for kids"]["score"])
        self.assertGreater(s["coloring book for kids"]["score"], s["coloring book for kids ages 4-8"]["score"])
        self.assertEqual(s["coloring book for adults"]["best_pos"], 1)

    def test_banned_terms_match_whole_words_only(self):
        banned = ["frozen", "abc", "learn", "paw patrol"]
        self.assertEqual(rn.banned_hit("frozen coloring book", banned), "frozen")
        self.assertEqual(rn.banned_hit("paw patrol coloring book", banned), "paw patrol")
        self.assertIsNone(rn.banned_hit("cabcar coloring book", banned))
        self.assertIsNone(rn.banned_hit("cozy winter coloring book", banned))
        real = rn.load_banned()
        self.assertTrue(real, "prompts/banned_terms.txt should exist")
        self.assertIsNotNone(rn.banned_hit("toddler coloring book numbers letters shapes", real))

    def test_worksheet_has_exact_columns_and_ten_rows_and_is_not_overwritten(self):
        p = rn.write_worksheet("bold and easy coloring book for adults", self.dir)
        rows = list(csv.reader(p.open()))
        self.assertEqual(rows[0], rn.WORKSHEET_COLUMNS)
        self.assertEqual(len(rows), 11)
        self.assertEqual(rows[10][:2], ["bold and easy coloring book for adults", "10"])
        p.write_text("keep me")
        rn.write_worksheet("bold and easy coloring book for adults", self.dir)
        self.assertEqual(p.read_text(), "keep me")

    def test_verdicts(self):
        p = self.dir / "k.csv"
        strong = {"bsr": "5,000", "reviews": "12,000", "price": "$7.99", "pages": "100", "pub_date": "2021-03-01"}
        small = {"bsr": "40000", "reviews": "60", "price": "9.99", "pages": "104", "pub_date": "2026-05-10"}
        dead = {"bsr": "900000", "reviews": "3", "price": "6.99", "pages": "60", "pub_date": "2026-01-01"}
        fill(p, "k", [strong] * 6 + [small] * 4)
        r = rn.rank_keyword(rn.read_worksheet(p), TODAY)
        self.assertEqual((r["verdict"], r["beatable"], r["selling"]), ("GO", 4, 10))
        self.assertEqual(r["median_price"], 7.99)
        fill(p, "k", [strong] * 9 + [small])
        self.assertEqual(rn.rank_keyword(rn.read_worksheet(p), TODAY)["verdict"], "MAYBE")
        fill(p, "k", [strong] * 10)
        self.assertEqual(rn.rank_keyword(rn.read_worksheet(p), TODAY)["verdict"], "NO")
        fill(p, "k", [dead] * 9 + [strong])
        self.assertEqual(rn.rank_keyword(rn.read_worksheet(p), TODAY)["verdict"], "NO")
        fill(p, "k", [small] * 3)
        self.assertEqual(rn.rank_keyword(rn.read_worksheet(p), TODAY)["verdict"], "UNVERIFIED")

    def test_report_ranks_verified_niches_first_and_drops_banned(self):
        data = {"date": "2026-11-14", "seeds": ["coloring book"], "queries": {
            "coloring book": ["coloring book for adults", "frozen coloring book", "cozy coloring book for adults"]}}
        small = {"bsr": "40000", "reviews": "60", "price": "9.99", "pages": "104", "pub_date": "2026-05-10"}
        fill(rn.worksheet_path("cozy coloring book for adults", self.dir), "cozy coloring book for adults", [small] * 6)
        report, kept = rn.build_report(data, ["frozen"], 10, self.dir, TODAY)
        self.assertEqual([k["phrase"] for k in kept], ["cozy coloring book for adults", "coloring book for adults"])
        self.assertIn("**GO** | cozy coloring book for adults", report)
        self.assertIn("**UNVERIFIED** | coloring book for adults", report)
        self.assertIn("frozen coloring book (frozen)", report)
        self.assertNotIn("| frozen coloring book |", report)

    def test_cli_rank_and_worksheet(self):
        h = self.dir / "h.json"
        h.write_text(json.dumps({"date": "d", "seeds": [], "queries": {"a": ["a b c"]}}))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(rn.main(["rank", str(h), "--worksheets", str(self.dir), "-o", str(self.dir / "r.md")]), 0)
            self.assertEqual(rn.main(["worksheet", "Some Keyword", "--worksheets", str(self.dir)]), 0)
        self.assertIn("a b c", (self.dir / "r.md").read_text())
        self.assertTrue((self.dir / "some-keyword.csv").is_file())


if __name__ == "__main__":
    unittest.main()
