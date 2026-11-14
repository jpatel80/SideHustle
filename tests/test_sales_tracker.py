"""Tests for scripts/sales_tracker.py."""
import contextlib
import datetime
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "sales_tracker", Path(__file__).resolve().parent.parent / "scripts" / "sales_tracker.py"
)
st = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(st)

TODAY = datetime.date(2027, 3, 1)
HEAD = "Royalty Date,Title,Author Name,ISBN,Marketplace,Royalty Type,Transaction Type,Units Sold,Units Refunded,Net Units Sold,Avg. List Price without tax,Royalty,Currency"


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.books = self.root / "books"
        self.reports = self.root / "tracking" / "kdp_reports"
        self.reports.mkdir(parents=True)
        for slug, title, pub in (("001-a", "Cozy Winter Animals Coloring Book", "2026-11-20"),
                                 ("002-b", "Cozy Cottage Coloring Book for Adults", "2026-12-01"),
                                 ("003-c", "Happy Ocean Animals Coloring Book", "2027-02-10"),
                                 ("004-d", "Unpublished Coloring Book", None)):
            (self.books / slug).mkdir(parents=True)
            (self.books / slug / "book.json").write_text(json.dumps({"title": title, "published": pub, "price_usd": 9.99}))

    def tearDown(self):
        self._tmp.cleanup()

    def report(self, name, lines, preamble=""):
        (self.reports / name).write_text(preamble + HEAD + "\n" + "\n".join(lines) + "\n")

    def run_report(self):
        rows = []
        for f in sorted(self.reports.glob("*")):
            rows += st.read_report(f)
        return st.build_report(st.load_books(self.books), rows, TODAY)

    def test_header_mapping_and_number_parsing(self):
        cols = st.map_headers(HEAD.split(","))
        self.assertEqual(cols["units"], 9)      # Net Units Sold, not Units Sold
        self.assertEqual(cols["royalty"], 11)   # Royalty, not Royalty Date / Royalty Type
        self.assertEqual(st.num("$1,234.50"), 1234.5)
        self.assertEqual(st.parse_date("2027-02"), datetime.date(2027, 2, 1))
        self.assertEqual(st.parse_date("02/14/2027"), datetime.date(2027, 2, 14))

    def test_decisions(self):
        self.report("feb.csv", [
            "2027-02-20,Cozy Cottage Coloring Book for Adults: 50 Bold and Easy Scenes,Clara,979,Amazon.com,60%,Standard,9,0,9,9.99,28.35,USD",
            "2027-02-25,Cozy Cottage Coloring Book for Adults: 50 Bold and Easy Scenes,Clara,979,Amazon.co.uk,60%,Standard,1,0,1,7.99,2.10,GBP",
            "2027-02-12,Happy Ocean Animals Coloring Book,Wren,979,Amazon.com,50%,Standard,2,0,2,6.99,1.32,USD",
            "2027-02-12,Somebody Else's Book,X,979,Amazon.com,50%,Standard,1,0,1,6.99,1.00,USD",
        ], preamble="Sales report\n\n")
        report, decisions = self.run_report()
        d = {x["slug"]: x for x in decisions}
        self.assertEqual(d["001-a"]["action"], "RETIRE NICHE")   # 101 days live, nothing sold
        self.assertEqual(d["002-b"]["action"], "SCALE")          # 10 copies in 30 days
        self.assertEqual(d["002-b"]["royalty_usd"], 28.35)
        self.assertEqual(d["002-b"]["royalty_other"], {"GBP": 2.1})
        self.assertEqual(d["003-c"]["action"], "TOO EARLY")
        self.assertEqual(d["004-d"]["action"], "NOT PUBLISHED")
        self.assertIn("a book is selling", report)
        self.assertIn("Somebody Else's Book", report)
        self.assertIn("| 2027-02 | 12 | $30.67 |", report)

    def test_hold_and_portfolio_stop_gate(self):
        self.report("jan.csv", ["2027-01-15,Cozy Winter Animals Coloring Book,Wren,979,Amazon.com,50%,Standard,1,0,1,7.99,1.16,USD"])
        report, decisions = self.run_report()
        d = {x["slug"]: x for x in decisions}
        self.assertEqual(d["001-a"]["action"], "HOLD")
        self.assertEqual(d["002-b"]["action"], "RETIRE NICHE")
        self.assertIn("STOP adding money", report)

    def test_overlapping_downloads_are_not_double_counted(self):
        line = "2027-02-20,Cozy Cottage Coloring Book for Adults,Clara,979,Amazon.com,60%,Standard,3,0,3,9.99,9.45,USD"
        self.report("mtd.csv", [line])
        self.report("full.csv", [line])
        _, decisions = self.run_report()
        self.assertEqual({x["slug"]: x for x in decisions}["002-b"]["units_total"], 3)

    def test_cli_writes_report_even_with_no_data(self):
        out = self.root / "tracking" / "REPORT.md"
        with contextlib.redirect_stdout(io.StringIO()):
            code = st.main(["--reports", str(self.reports), "--books", str(self.books), "-o", str(out), "--today", "2026-11-14"])
        self.assertEqual(code, 0)
        self.assertIn("NOT PUBLISHED", out.read_text())


if __name__ == "__main__":
    unittest.main()
